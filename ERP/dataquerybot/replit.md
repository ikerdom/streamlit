# Overview

Chat SQL is an intelligent database query application that enables users to interact with databases using natural language in Spanish. The system converts Spanish questions into SQL queries using OpenAI's GPT-5 model and provides visual representations of query results. It supports both PostgreSQL and SQL Server databases with automatic database type detection and connection management.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Streamlit Framework**: Web-based interface for user interactions with real-time chat functionality
- **Session State Management**: Maintains connection status, chat history, and service instances across user sessions
- **Multi-page Layout**: Wide layout configuration optimized for data visualization and query results

## Backend Architecture
- **Multi-database Support**: Unified interface supporting both PostgreSQL and SQL Server with automatic detection
- **Connection Management**: Environment variable-based configuration with fallback connection strategies
- **Schema Introspection**: Dynamic schema discovery using INFORMATION_SCHEMA queries for both database types
- **Query Execution**: Safe SQL execution with result limiting and error handling

## AI Integration
- **OpenAI GPT-5 Integration**: Natural language to SQL conversion with Spanish language support
- **Context-Aware Prompting**: Schema-aware prompt engineering with strict mode for enhanced accuracy
- **Query Validation**: SQL syntax validation and table/column name verification against database schema

## Data Visualization
- **Plotly Integration**: Interactive charts including bar charts, pie charts, and line graphs
- **Automatic Chart Selection**: Intelligent column type detection for appropriate visualization selection
- **Result Analysis**: Statistical summaries and data insights for query results

## Database Connection Strategy
- **PostgreSQL**: Primary support via DATABASE_URL or individual connection parameters
- **SQL Server**: DSN-based or manual connection string construction with integrated security
- **Connection Pooling**: Persistent connections with automatic reconnection handling

## Error Handling and Recovery
- **Query Retry Logic**: Automatic retry with corrected table/column names when invalid identifiers are detected
- **Graceful Degradation**: Fallback mechanisms for visualization failures and connection issues
- **Comprehensive Logging**: Detailed error tracking and debugging information

# External Dependencies

## AI Services
- **OpenAI API**: GPT-5 model for natural language processing and SQL generation
- **API Key Management**: Environment variable-based authentication

## Database Drivers
- **PostgreSQL**: psycopg2 for PostgreSQL connectivity
- **SQL Server**: pyodbc with ODBC Driver support for Windows and cross-platform compatibility

## Data Processing
- **Pandas**: Data manipulation and analysis for query results
- **NumPy**: Numerical computing support for data operations

## Visualization
- **Plotly Express**: High-level plotting interface for quick visualizations
- **Plotly Graph Objects**: Advanced chart customization and interactive features

## Web Framework
- **Streamlit**: Complete web application framework with built-in state management
- **Session Management**: Persistent user sessions and real-time updates

## Environment Configuration
- **Database Connection**: Environment variables for flexible database configuration
- **API Keys**: Secure credential management through environment variables
- **Query Limits**: Configurable result set limitations via SQL_TOP_DEFAULT