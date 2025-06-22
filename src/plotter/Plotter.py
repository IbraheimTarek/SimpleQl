from __future__ import annotations
import json, uuid, os
from dataclasses import dataclass
from typing import ClassVar
import pandas as pd
import matplotlib.pyplot as plt
from pydantic import Field, PrivateAttr, BaseModel
from langchain.tools import BaseTool
from langchain.prompts import PromptTemplate
from langchain_groq import ChatGroq
from dotenv import load_dotenv
# Global variable for plot directory
PLOT_DIR = "plots"
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")

#  tiny helpers 
def summarise_dataframe(df: pd.DataFrame, max_categories: int = 10) -> dict:
    """Return lightweight, LLM-safe stats for each column."""
    summary = {"n_rows": len(df), "columns": []}
    for col in df.columns:
        dtype = str(df[col].dtype)
        info = {"name": col, "dtype": dtype}
        if pd.api.types.is_numeric_dtype(df[col]):
            info |= {
                "min": df[col].min(),
                "max": df[col].max(),
                "mean": df[col].mean(),
                "std": df[col].std(),
            }
        else:
            vc = df[col].value_counts().head(max_categories)
            info["top_categories"] = vc.to_dict()
        summary["columns"].append(info)
    return summary



def _ensure_plot_dir():
    if not os.path.exists(PLOT_DIR):
        os.makedirs(PLOT_DIR, exist_ok=True)

def _plot_histogram(df: pd.DataFrame, column: str, bins: int = 30) -> str:
    _ensure_plot_dir()
    fig, ax = plt.subplots()
    ax.hist(df[column].dropna(), bins=bins)
    ax.set_title(f"Histogram of {column}")
    path = os.path.join(PLOT_DIR, f"hist_{uuid.uuid4().hex}.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path

def _plot_pie(df: pd.DataFrame, column: str, top: int = 10) -> str:
    _ensure_plot_dir()
    counts = df[column].value_counts().head(top)
    fig, ax = plt.subplots()
    ax.pie(counts, labels=counts.index, autopct=lambda p: f"{p:.1f}%")
    ax.set_title(f"Categories of {column}")
    path = os.path.join(PLOT_DIR, f"pie_{uuid.uuid4().hex}.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


_PLOTTERS = {"histogram": _plot_histogram, "pie": _plot_pie}

#  prompt and response schema 
VIZ_PROMPT = PromptTemplate(
    input_variables=["question", "summary"],
    template="""
You are a data-visualisation assistant.

The user asked: "{question}"

You will NOT receive raw rows - only this summary:
{summary}

Return exactly one JSON object describing the best single plot.
Allowed plot types: "histogram", "pie".
JSON schema:
{{
  "plot":  "histogram|pie",
  "column": "<column name>",
  "bins":   <int>      # optional, histogram only
}}
No extra keys, no markdown, no prose.
""",
)


@dataclass
class _VizPlan:
    plot: str
    column: str
    bins: int | None = None



class _VizArgs(BaseModel):

    # the only *public* (Pydantic) field the tool expects at run-time
    request: str = Field(
        default="",
        description="Natural-language instruction for the chart",
    )


class DataVizTool(BaseTool):
    """
    LangChain Tool that keeps a DataFrame private and renders a chart
    chosen by an LLM from a summary of that DataFrame.
    """

    # static meta
    name: ClassVar[str] = "data_visualiser"
    description: ClassVar[str] = "Generate and render charts from tabular data."
    model_config = {"arbitrary_types_allowed": True}
    args_schema: ClassVar[type[BaseModel]] = _VizArgs


    # private runtime attributes
    _df: pd.DataFrame = PrivateAttr()
    _llm: ChatGroq = PrivateAttr()

    def __init__(
        self,
        df: pd.DataFrame,
        llm: ChatGroq | None = None,
    ):
        super().__init__(request="")  # initialise BaseTool
        self._df = df
        self._llm = llm or ChatGroq(
            groq_api_key=groq_api_key,
            model_name="llama3-70b-8192",
            temperature=0,
        )

    # synchronous execution (what run() ultimately calls)
    def _run(self, request: str) -> str:
        summary = summarise_dataframe(self._df)
        plan_json = self._llm.invoke(
            VIZ_PROMPT.format(
                question=request, summary=json.dumps(summary, indent=2)
            )
        )
        plan = _VizPlan(**json.loads(getattr(plan_json, "content", plan_json)))

        if plan.plot not in _PLOTTERS:
            raise ValueError(f"Unsupported plot type: {plan.plot}")

        #  prepare kwargs just for the chosen plot type 
        if plan.plot == "histogram":
            img = _plot_histogram(self._df, plan.column, bins=plan.bins or 30)

        elif plan.plot == "pie":
            top = plan.bins or 10                     # reuse bins as top
            img = _plot_pie(self._df, plan.column, top=top)

        else:                                         # future-proof
            img = _PLOTTERS[plan.plot](self._df, plan.column)

        return img
    

if __name__ == "__main__":
    df_result = pd.DataFrame({
        # numeric values for a histogram
        "rating_score": [4.0, 3.5, 5.0, 2.5, 3.0, 4.5, 5.0, 2.0, 4.0, 3.5,
                        4.5, 3.0, 2.5, 2.0, 4.0, 5.0, 3.5, 3.0, 4.5, 1.5],
        # quick categorical bucket for a pie chart
        "rating_bucket": [
            "4-5", "3-4", "4-5", "2-3", "3-4", "4-5", "4-5", "2-3", "4-5", "3-4",
            "4-5", "3-4", "2-3", "1-2", "4-5", "4-5", "3-4", "3-4", "4-5", "1-2"
        ],
    })
    viz_tool = DataVizTool(df_result)
    hist_path = viz_tool.run("Plot a histogram of rating_score")
    print("Histogram saved to:", hist_path)
    pie_path = viz_tool.run("Plot a pie chart of rating_bucket")
    print("Pie chart saved to:", pie_path)