import os, uuid, re, itertools
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import ClassVar
from pydantic import PrivateAttr
from langchain.tools import BaseTool
import re 

class DataVizTool(BaseTool):
    name: ClassVar[str] = "auto_data_visualiser"
    description: ClassVar[str] = "Automatically generate all relevant visualizations from tabular data."
    model_config = {"arbitrary_types_allowed": True}
    _df: pd.DataFrame = PrivateAttr()
    _plots_dir: str = PrivateAttr()

    def __init__(self, df : pd.DataFrame, plots_dir= "plots"):
        super().__init__()
        self._df = df
        self._plots_dir = plots_dir

    def _run(self, request: str) -> str:
        info_list = []
        if self._df.shape[0] > 1: 
            for col in self._df.columns:
                dtype = self._df[col].dtype
                nunique = self._df[col].nunique()
                uniqued=False
                if nunique==self._df.shape[0]:
                    uniqued=True
                    
                info_list.append((col, dtype, nunique,uniqued,nunique/self._df.shape[0]))
        info_df = pd.DataFrame(info_list, columns=['Column Name', 'Data Type', 'UniqueValues','Is_Unique_valued','unique_over_size'])

        #### Exclude columns
        valid_cols = info_df.copy()

        if len(valid_cols)==0:
            return "No plots needed"
        valid_cols = valid_cols[~valid_cols["Column Name"].str.lower().apply(self.is_id_column)]
        # one valued 
        if len(valid_cols)==0:
            return "No plots needed"
        valid_cols = valid_cols[~(valid_cols['UniqueValues'] == 1)]

        if len(valid_cols)==0:
            return "No plots needed"
        

        
        num_cols = valid_cols[valid_cols["Data Type"].apply(lambda x: np.issubdtype(np.dtype(x), np.number))]["Column Name"].tolist()
        cat_cols = valid_cols[valid_cols["Data Type"].apply(lambda x: not np.issubdtype(np.dtype(x), np.number))]["Column Name"].tolist()

        # Shorten categorical values in the dataframe
        for col in cat_cols:
            self._df[col] = self._df[col].apply(lambda x: self.shorten_label(x, max_len=10))


        generated_plots = []

        # Single Categorical
        for col in cat_cols:
            path = self.vis_single_cat(self._df, col)
            generated_plots.append(path)

        # Pairwise Numeric
        for col1, col2 in itertools.combinations(num_cols, 2):
            path = self.vis_two_num(self._df, col1, col2)
            generated_plots.append(path)

        # Pairwise Categorical
        for col1, col2 in itertools.combinations(cat_cols, 2):
            path = self.vis_two_cat(self._df, col1, col2)
            generated_plots.append(path)

        # Numeric vs Categorical
        for num_col in num_cols:
            for cat_col in cat_cols:
                path = self.vis_cat_num(self._df, cat_col, num_col)
                generated_plots.append(path)

        return f"Generated {len(generated_plots)} plots: {generated_plots}"

    # tiny helpers 
    def _ensure_plot_dir(self):
        if not os.path.exists(self._plots_dir):
            os.makedirs(self._plots_dir, exist_ok=True)

    def is_id_column(self, colname):
        colname = colname.lower()
        pattern = r'(^id$|^id[\-_].*|.*[\-_]id$|.*[\-_]id[\-_].*|.*id$)'
        return bool(re.match(pattern, colname))

    def shorten_label(self, label, max_len=11):
        if not isinstance(label, str):
            return label  
        return label if len(label) <= max_len else label[:max_len].rstrip() + "..."
    

    def vis_single_cat(self, df, col, target_col=None):
        # Drop NA to avoid counting them as unique
        non_null_values = df[col].dropna()
        unique_ratio = non_null_values.nunique() / len(non_null_values)

        # Return early if uniqueness is too high
        if unique_ratio >= 0.95:
            return None

        value_counts = non_null_values.value_counts()
        self._ensure_plot_dir()

        if len(value_counts) > 25:
            # Group top 25 values, rest to 'Other'
            top_25 = value_counts.head(25).index
            df[col] = df[col].apply(lambda x: x if x in top_25 else 'Other')
            value_counts = df[col].value_counts()

        if len(value_counts) <= 10:
            plt.figure(figsize=(6, 6))
            value_counts.plot.pie(autopct='%1.1f%%', startangle=90)
            plt.title(f'Pie plot of {col}')
            plt.ylabel('')
        else:
            plt.figure(figsize=(10, 5))
            sns.countplot(data=df, x=col, order=value_counts.index)
            plt.title(f'Bar Plot for {col}')
            plt.xticks(rotation=45)

        path = os.path.join(self._plots_dir, f"{col}_cat_{uuid.uuid4().hex}.png")
        plt.savefig(path, bbox_inches="tight")
        plt.close()
        return path

    def vis_two_cat(self, df, col1, col2):
        self._ensure_plot_dir()
        n1 = df[col1].nunique()
        n2 = df[col2].nunique()

        if n1 < 10 and n2 < 10:
            ct = pd.crosstab(df[col1], df[col2])
            ct.plot(kind='bar', figsize=(10, 6))
            plt.title(f'Grouped Bar Plot: {col1} vs {col2}')
            plt.xlabel(col1)
            plt.ylabel('Count')
            plt.xticks(rotation=45)
            plt.legend(title=col2)
            plt.tight_layout()

        elif n1 < 10 and n2 >= 10:
            top_col2 = df[col2].value_counts().nlargest(10).index
            df_filtered = df[df[col2].isin(top_col2)]
            plt.figure(figsize=(12, 6))
            sns.countplot(data=df_filtered, x=col2, hue=col1, order=top_col2)
            plt.title(f'Top 10 {col2} by {col1}')
            plt.xticks(rotation=45)
            plt.tight_layout()

        elif n2 < 10 and n1 >= 10:
            top_col1 = df[col1].value_counts().nlargest(10).index
            df_filtered = df[df[col1].isin(top_col1)]
            plt.figure(figsize=(12, 6))
            sns.countplot(data=df_filtered, x=col1, hue=col2, order=top_col1)
            plt.title(f'Top 10 {col1} by {col2}')
            plt.xticks(rotation=45)
            plt.tight_layout()

        else:
            ct = pd.crosstab(df[col1], df[col2])
            top_rows = ct.sum(axis=1).nlargest(10).index
            top_cols = ct.sum(axis=0).nlargest(10).index
            ct_filtered = ct.loc[top_rows, top_cols]
            plt.figure(figsize=(10, 8))
            sns.heatmap(ct_filtered, annot=True, fmt='d', cmap='Blues')
            plt.title(f'Heatmap of Top 10 {col1} vs Top 10 {col2}')
            plt.xlabel(col2)
            plt.ylabel(col1)
            plt.tight_layout()

            path = os.path.join(self._plots_dir, f"{col1}_{col2}_2cat_{uuid.uuid4().hex}.png")
            plt.savefig(path, bbox_inches="tight")
            plt.close()
            return path


    def vis_two_num(self, df, col1, col2):
        self._ensure_plot_dir()
        threshold = 1000

        sub_df = df[[col1, col2]].dropna()
        n_points = len(sub_df)
        corr = sub_df.corr().iloc[0, 1]

        plt.figure(figsize=(8, 6))

        if n_points <= threshold:
            sns.scatterplot(x=col1, y=col2, data=sub_df)
            plt.title(f'Scatter Plot: {col1} vs {col2} (corr={corr:.2f})')
        else:
            sns.kdeplot(x=sub_df[col1], y=sub_df[col2], cmap="Blues", fill=True, thresh=0.05)
            plt.title(f'2D Density Plot: {col1} vs {col2} (corr={corr:.2f})')

        plt.xlabel(col1)
        plt.ylabel(col2)
        plt.tight_layout()

        path = os.path.join(self._plots_dir, f"{col1}_{col2}_2num_{uuid.uuid4().hex}.png")
        plt.savefig(path, bbox_inches="tight")
        plt.close()
        return path


    def vis_cat_num(self, df, cat_col, num_col):
        self._ensure_plot_dir()

        # Drop missing values
        sub_df = df[[cat_col, num_col]].dropna()

        # Count unique categories
        unique_vals = sub_df[cat_col].nunique()
        threshold = 14

        # Group rare categories into 'Other'
        if unique_vals > threshold:
            top_categories = sub_df[cat_col].value_counts().nlargest(threshold).index
            sub_df[cat_col] = sub_df[cat_col].where(sub_df[cat_col].isin(top_categories), other='Other')

        plt.figure(figsize=(10, 6))
        sns.violinplot(x=cat_col, y=num_col, data=sub_df,cut=0)
        plt.title(f'Violin Plot of {num_col} by {cat_col}')
        plt.xticks(rotation=45)
        plt.tight_layout()

        path = os.path.join(self._plots_dir, f"{num_col}_{cat_col}_catnum_{uuid.uuid4().hex}.png")
        plt.savefig(path, bbox_inches="tight")
        plt.close()

        return path



if __name__ == "__main__":
    # to test 
    df_result = pd.DataFrame({
    'gender': np.random.choice(['Male', 'Female'], size=20),
    'age': np.random.randint(18, 65, size=20),
    'department': np.random.choice(['HR', 'IT', 'Sales', 'Finance'], size=20),
    'salary': np.random.randint(30000, 100000, size=20),
    'status': np.random.choice(
        ['Active', 'Inactive', 'On Leave', 'Fired', 'Retired', 'Suspended',
         'Pending', 'Resigned', 'Training', 'Intern', 'Part-time', 'Contract'], size=20),
    'rating': np.round(np.random.uniform(1.0, 5.0, size=20), 1),
    'region': np.random.choice(['East', 'West', 'North', 'South', 'Central', 'Northeast', 'Southwest', 'Midwest'], size=20),
    'team': np.random.choice([f'Team{i}' for i in range(1, 16)], size=20)
})

    viz_tool = DataVizTool(df_result)
    result = viz_tool.run("Plot automatically")
