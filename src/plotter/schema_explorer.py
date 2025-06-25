from __future__ import annotations
import shutil, textwrap, tempfile, webbrowser
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from Params import DB_PATH
from database_manager import DBManager
from graphviz import Digraph
from pyvis.network import Network
import jinja2, pyvis, sys




class SchemaExplorer:
    """
    Visualises a DBManager.schema and its  relationships.
    """

    def __init__(self, dbm: "DBManager"):
        self.schema: Dict[str, Dict[str, str]] = dbm.schema
        self.pks:     Dict[str, List[str]]      = dbm.primary_keys
        self.fks:     Dict[str, List[Tuple[str, str]]] = dbm.foreign_keys
        self.db_name = dbm.db_name

    #Console tree view

    def print_tree(self, wrap: int = 80) -> None:
        """
        Pretty-prints a table/column hierarchy with PK / FK markers.

        Output looks like:
            Orders
            |->OrderID (PK)
            |->CustomerID → Customers.CustomerID
            |->OrderDate
        """
        for t, cols in self.schema.items():
            print(f"{t}")
            fk_map = {src.split(".")[1]: dst for src, dst in self.fks.get(t, [])}
            for i, col in enumerate(cols):
                bullet = "└─" if i == len(cols)-1 else "├─"
                label = f"{bullet} {col}"
                if col in self.pks.get(t, []):
                    label += " (PK)"
                if col in fk_map:
                    label += f" → {fk_map[col]}"
                print("  " + textwrap.fill(label, wrap, subsequent_indent="    "))
            print()

    # Static ER diagram (Graphviz)
    def render_er(
        self,
        out_path: str | Path,
        format_: str = "png",
        open_file: bool = False,
    ) -> Optional[Path]:
        """
        Renders an ERdiagram using Graphviz.
        Returns the output Path if it was there.
        """
        if Digraph is None:
            print("graphviz not installed")
            return None


        dot = Digraph(
            name=self.db_name,
            graph_attr={"rankdir": "LR", "splines": "ortho"},
            node_attr={"shape": "record", "fontsize": "10", "fontname": "Helvetica"},
        )

        # add table nodes
        for t, cols in self.schema.items():
            pk_set = set(self.pks.get(t, []))
            col_lines = []
            for c in cols:
                mark = "." if c in pk_set else " "
                col_lines.append(f"{mark}{c}")
            #single braces 
            label = "{" + t + "|" + "\\l".join(col_lines) + "\\l}"
            dot.node(t, label=label)

        # add foreign-key edges
        for t, links in self.fks.items():
            for src, dst in links:
                src_tbl, src_col = src.split(".")
                dst_tbl, dst_col = dst.split(".")
                dot.edge(src_tbl, dst_tbl, taillabel=src_col, headlabel=dst_col, arrowhead="normal", arrowsize="0.7")

        out_path = Path(out_path).with_suffix(f".{format_}")
        dot.render(out_path.with_suffix(""), format=format_, cleanup=True)
        if open_file:
            self._open_file(out_path)
        print(f"ER diagram written to {out_path}")
        return out_path

    # Interactive HTML (pyvis)
    def render_html(self, out_path: str | Path, open_file: bool = True):
        if Network is None:
            print("pyvis not installed;")
            return None
        try:
            import jinja2  # ensure dependency exists
        except ImportError:
            print("Jinja2 missing ")
            return None

        net = Network(height="750px", width="100%", directed=True)
        net.force_atlas_2based(gravity=-50, spring_length=150)

        for t, cols in self.schema.items():
            pk_set = set(self.pks.get(t, []))
            html_cols = "<br>".join(
                f"<b>{c}</b>" if c in pk_set else c for c in cols
            )
            net.add_node(t, label=t, title=html_cols, shape="box", color="#AED6F1")
        for t, links in self.fks.items():
            for src, dst in links:
                dst_tbl = dst.split(".")[0]
                net.add_edge(t, dst_tbl, arrowStrikethrough=False)

        out_path = Path(out_path).with_suffix(".html")

        net.write_html(str(out_path), open_browser=open_file, notebook=False)

        print(f"Interactive diagram written to {out_path}")
        return out_path


    @staticmethod
    def _open_file(path: Path):
        try:
            webbrowser.open_new_tab(path.as_uri())
        except Exception:
            print(f"Open {path} manually.")

    def run(self):
        base_dir = Path("plots/schema_explorer")

        db_dir   = base_dir / self.db_name    # dedicated folder per DB

        db_dir.mkdir(parents=True, exist_ok=True)

        png_path  = db_dir / "schema.png"
        
        html_path = db_dir / "schema.html"

        self.print_tree()

        if png_path.exists():
            print(f" PNG diagram already exists ->{png_path}")
        else:
            self.render_er(png_path)

        if html_path.exists():
            print(f"HTML diagram already exists -> {html_path}")
        else:
            self.render_html(html_path)

if __name__ == "__main__":

    dbm = DBManager(DB_PATH)
    viz = SchemaExplorer(dbm)
    viz.run()

