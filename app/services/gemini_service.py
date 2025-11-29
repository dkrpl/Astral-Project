import google.generativeai as genai
from app.config import settings
from app.services.database_service import DatabaseService
import json
import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-pro')
        
    async def analyze_universal_schema(self, table_schema: dict) -> Dict[str, Any]:
        """Analyze ANY database schema without assumptions"""
        
        prompt = f"""
        DATABASE SCHEMA ANALYSIS:
        {json.dumps(table_schema, indent=2, ensure_ascii=False)}
        
        Analyze this database schema COMPLETELY NEUTRAL - no business assumptions.
        Just understand the table structures and relationships.
        
        Return ONLY JSON:
        {{
            "detected_tables": ["table1", "table2"],
            "table_relationships": {{
                "table1": ["related_field1", "related_field2"]
            }},
            "key_entities": ["main_entity1", "main_entity2"],
            "schema_pattern": "description of schema pattern"
        }}
        """
        
        try:
            response = self.model.generate_content(prompt)
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {"detected_tables": list(table_schema.keys())}
        except Exception as e:
            logger.error(f"Error analyzing schema: {str(e)}")
            return {"detected_tables": list(table_schema.keys())}
    
    async def generate_universal_sql(self, user_query: str, table_schema: dict) -> str:
        """Generate SQL for ANY database type and structure"""
        
        prompt = f"""
        DATABASE SCHEMA (ALL TABLES):
        {json.dumps(table_schema, indent=2, ensure_ascii=False)}
        
        USER QUESTION: "{user_query}"
        
        INSTRUCTIONS:
        1. Look at ALL available tables and columns
        2. Generate the MOST RELEVANT SQL query based on user's intent
        3. Use actual table and column names from the schema
        4. Make intelligent guesses about relationships
        5. Focus on answering the user's question directly
        6. Return ONLY the SQL query, nothing else
        
        IMPORTANT: Don't assume business context. Just use the schema structure.
        
        SQL QUERY:
        """
        
        try:
            response = self.model.generate_content(prompt)
            sql_query = response.text.strip()
            
            # Clean up
            sql_query = re.sub(r'```sql|```', '', sql_query).strip()
            logger.info(f"Generated universal SQL: {sql_query}")
            return sql_query
        except Exception as e:
            logger.error(f"Error generating SQL: {str(e)}")
            # Fallback: simple query to get table info
            tables = list(table_schema.keys())
            if tables:
                return f"SELECT * FROM {tables[0]} LIMIT 10"
            return "SELECT 1"
    
    async def generate_direct_response(self, user_query: str, query_result: dict, sql_query: str, table_schema: dict) -> str:
        """Generate response that directly answers based on data"""
        
        prompt = f"""
        USER QUESTION: "{user_query}"
        EXECUTED SQL: {sql_query}
        QUERY RESULTS: {json.dumps(query_result, indent=2, ensure_ascii=False)}
        AVAILABLE TABLES: {list(table_schema.keys())}
        
        Provide a DIRECT ANSWER in Indonesian:
        1. Answer the user's question clearly based on the data
        2. If data is available, present it clearly
        3. If no data found, suggest what might be available
        4. Keep it simple and factual
        5. Don't make assumptions about business context
        6. Format numbers nicely
        
        DIRECT ANSWER:
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            # Ultra simple fallback
            if query_result.get('success') and 'data' in query_result:
                data = query_result['data']
                if data:
                    return f"Ditemukan {len(data)} record. Data: {str(data)[:200]}..."
            return f"Query berhasil: {query_result.get('message', 'Completed')}"
    
    async def process_universal_chat(self, user_query: str, db_service: DatabaseService) -> dict:
        """Universal chat processing for ANY database"""
        
        try:
            # Get schema dynamically
            schema_result = await db_service.get_table_schema()
            table_schema = schema_result.get('schema', {}) if schema_result.get('success') else {}
            
            if not table_schema:
                return {
                    "response": "Database terhubung tetapi tidak ada tabel yang terdeteksi. Pastikan database memiliki tabel.",
                    "sql_query": None,
                    "query_result": None,
                    "success": False
                }
            
            # Generate SQL based on actual schema
            sql_query = await self.generate_universal_sql(user_query, table_schema)
            
            # Execute query
            query_result = await db_service.execute_query(sql_query)
            
            # Generate direct response
            natural_response = await self.generate_direct_response(
                user_query, query_result, sql_query, table_schema
            )
            
            return {
                "response": natural_response,
                "sql_query": sql_query,
                "query_result": query_result,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error in universal chat: {str(e)}")
            return {
                "response": f"Error memproses permintaan: {str(e)}",
                "sql_query": None,
                "query_result": None,
                "success": False
            }