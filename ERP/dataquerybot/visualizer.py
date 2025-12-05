import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional

class ResultVisualizer:
    """Creates visualizations from SQL query results"""
    
    def __init__(self, data: pd.DataFrame):
        self.data = data
        
    def create_bar_chart(self) -> Optional[go.Figure]:
        """Create a bar chart from the data"""
        if self.data.empty:
            return None
            
        try:
            # Try to find appropriate columns for bar chart
            numeric_cols = self.data.select_dtypes(include=['number']).columns.tolist()
            text_cols = self.data.select_dtypes(include=['object', 'category']).columns.tolist()
            
            if len(numeric_cols) == 0:
                return None
            
            # Need at least one text column or multiple rows for meaningful bar chart
            if len(text_cols) == 0 and len(self.data) <= 1:
                return None
            
            # Use first text column as x-axis, first numeric column as y-axis
            x_col = text_cols[0] if text_cols else self.data.columns[0]
            y_col = numeric_cols[0]
            
            # Limit to top 20 items for readability
            plot_data = self.data.nlargest(20, y_col) if len(self.data) > 20 else self.data
            
            fig = px.bar(
                plot_data,
                x=x_col,
                y=y_col,
                title=f"{y_col} por {x_col}",
                labels={str(x_col): str(x_col), str(y_col): str(y_col)}
            )
            
            fig.update_layout(
                xaxis_tickangle=-45,
                height=400
            )
            
            return fig
            
        except Exception:
            return None
    
    def create_pie_chart(self) -> Optional[go.Figure]:
        """Create a pie chart from the data"""
        if self.data.empty:
            return None
            
        try:
            # Find columns suitable for pie chart
            numeric_cols = self.data.select_dtypes(include=['number']).columns.tolist()
            text_cols = self.data.select_dtypes(include=['object', 'category']).columns.tolist()
            
            if len(numeric_cols) == 0 or len(text_cols) == 0:
                return None
            
            # Use first text column for labels, first numeric column for values
            labels_col = text_cols[0]
            values_col = numeric_cols[0]
            
            # Group by labels and sum values if needed
            pie_data = self.data.groupby(labels_col)[values_col].sum().reset_index()
            
            # Limit to top 10 items for readability
            if len(pie_data) > 10:
                pie_data = pie_data.nlargest(10, values_col)
            
            fig = px.pie(
                pie_data,
                values=values_col,
                names=labels_col,
                title=f"Distribución de {values_col} por {labels_col}"
            )
            
            fig.update_layout(height=400)
            
            return fig
            
        except Exception:
            return None
    
    def create_line_chart(self) -> Optional[go.Figure]:
        """Create a line chart from the data"""
        if self.data.empty:
            return None
            
        try:
            # Find columns suitable for line chart
            numeric_cols = self.data.select_dtypes(include=['number']).columns.tolist()
            date_cols = self.data.select_dtypes(include=['datetime64']).columns.tolist()
            
            if len(numeric_cols) == 0:
                return None
            
            # Prefer date columns for x-axis, otherwise use first column
            if date_cols:
                x_col = date_cols[0]
            else:
                # Try to find a column that might represent time/sequence
                potential_x_cols = [col for col in self.data.columns 
                                   if any(word in col.lower() for word in ['fecha', 'date', 'tiempo', 'time', 'año', 'year', 'mes', 'month'])]
                x_col = potential_x_cols[0] if potential_x_cols else self.data.columns[0]
            
            y_col = numeric_cols[0]
            
            # Sort by x-axis for better line visualization
            plot_data = self.data.sort_values(str(x_col))
            
            fig = px.line(
                plot_data,
                x=x_col,
                y=y_col,
                title=f"Tendencia de {y_col} a lo largo del tiempo",
                labels={str(x_col): str(x_col), str(y_col): str(y_col)}
            )
            
            fig.update_layout(
                height=400,
                xaxis_tickangle=-45
            )
            
            return fig
            
        except Exception:
            return None
    
    def create_histogram(self) -> Optional[go.Figure]:
        """Create a histogram from numeric data"""
        if self.data.empty:
            return None
            
        try:
            numeric_cols = self.data.select_dtypes(include=['number']).columns.tolist()
            
            if len(numeric_cols) == 0:
                return None
            
            col = numeric_cols[0]
            
            fig = px.histogram(
                self.data,
                x=col,
                title=f"Distribución de {col}",
                labels={col: col}
            )
            
            fig.update_layout(height=400)
            
            return fig
            
        except Exception:
            return None
    
    def create_scatter_plot(self) -> Optional[go.Figure]:
        """Create a scatter plot from numeric data"""
        if self.data.empty:
            return None
            
        try:
            numeric_cols = self.data.select_dtypes(include=['number']).columns.tolist()
            
            if len(numeric_cols) < 2:
                return None
            
            x_col = numeric_cols[0]
            y_col = numeric_cols[1]
            
            fig = px.scatter(
                self.data,
                x=x_col,
                y=y_col,
                title=f"Relación entre {x_col} y {y_col}",
                labels={x_col: x_col, y_col: y_col}
            )
            
            fig.update_layout(height=400)
            
            return fig
            
        except Exception:
            return None
