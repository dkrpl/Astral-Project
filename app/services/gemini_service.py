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
        # Use the most powerful available model
        try:
            self.model = genai.GenerativeModel('gemini-2.0-flash')
        except:
            self.model = genai.GenerativeModel('gemini-pro')
        
    async def explore_database_adaptively(self, db_service: DatabaseService) -> Dict[str, Any]:
        """Explore database adaptively to understand its content"""
        try:
            # Get schema first
            schema_result = await db_service.get_table_schema()
            table_schema = schema_result.get('schema', {}) if schema_result.get('success') else {}
            
            if not table_schema:
                return {"status": "no_tables", "tables": []}
            
            # Get sample data from each table to understand content
            database_content = {}
            sample_insights = []
            
            for table_name, table_info in table_schema.items():
                try:
                    # Get sample data
                    result = await db_service.execute_query(f"SELECT * FROM {table_name} LIMIT 3")
                    if result.get('success') and result.get('data'):
                        sample_data = result['data']
                        database_content[table_name] = {
                            'columns': table_info.get('columns', []),
                            'sample_data': sample_data,
                            'sample_size': len(sample_data)
                        }
                        
                        # Analyze sample data for insights
                        if sample_data:
                            sample_insights.append(f"Tabel {table_name}: {len(sample_data)} sample records dengan kolom {table_info.get('columns', [])}")
                            
                except Exception as e:
                    logger.warning(f"Could not sample table {table_name}: {e}")
                    continue
            
            return {
                "status": "success",
                "tables": list(table_schema.keys()),
                "table_count": len(table_schema),
                "database_content": database_content,
                "sample_insights": sample_insights
            }
            
        except Exception as e:
            logger.error(f"Error exploring database: {e}")
            return {"status": "error", "error": str(e)}
    
    async def process_free_form_chat(self, user_query: str, db_service: DatabaseService) -> dict:
        """Process ANY user question and adapt to the database"""
        
        try:
            # First, explore what's in the database
            db_exploration = await self.explore_database_adaptively(db_service)
            
            if db_exploration.get('status') == 'no_tables':
                return {
                    "response": "Saya sudah terhubung ke database, tetapi tidak menemukan tabel apapun. Pastikan database Anda berisi tabel, atau mungkin database yang berbeda?",
                    "sql_query": None,
                    "query_result": None,
                    "success": True
                }
            
            # Prepare context about the database
            db_context = self._prepare_database_context(db_exploration)
            
            # Generate adaptive response based on user query and database content
            prompt = self._build_adaptive_prompt(user_query, db_context, db_exploration)
            
            # Get AI response
            response = self.model.generate_content(prompt)
            ai_response = response.text.strip()
            
            # Check if AI wants to execute SQL
            sql_query = self._extract_sql_query(ai_response)
            query_result = None
            
            if sql_query:
                # Execute the suggested SQL
                query_result = await db_service.execute_query(sql_query)
                
                # If we got data, enhance the response
                if query_result.get('success') and query_result.get('data'):
                    enhanced_response = await self._enhance_with_data(ai_response, query_result, user_query)
                    if enhanced_response:
                        ai_response = enhanced_response
            
            return {
                "response": ai_response,
                "sql_query": sql_query,
                "query_result": query_result,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error in free form chat: {str(e)}")
            return {
                "response": f"❌ Maaf, ada gangguan teknis: {str(e)}",
                "sql_query": None,
                "query_result": None,
                "success": False
            }
    
    def _prepare_database_context(self, db_exploration: Dict[str, Any]) -> str:
        """Prepare context about what's in the database"""
        if db_exploration.get('status') != 'success':
            return "Database tidak dapat diakses"
        
        tables = db_exploration.get('tables', [])
        table_count = db_exploration.get('table_count', 0)
        sample_insights = db_exploration.get('sample_insights', [])
        
        context = f"Database memiliki {table_count} tabel: {', '.join(tables)}"
        
        if sample_insights:
            context += "\n\nSample data yang terdeteksi:\n" + "\n".join(sample_insights)
        
        return context
    
    def _build_adaptive_prompt(self, user_query: str, db_context: str, db_exploration: Dict[str, Any]) -> str:
        """Build adaptive prompt based on user question and database content"""
        
        prompt = f"""
        Anda adalah asisten AI yang sangat fleksibel dan adaptif. User dapat bertanya APA SAJA, dan Anda harus merespons dengan cara yang paling membantu berdasarkan database yang tersedia.

        KONTEKS DATABASE:
        {db_context}

        ISI DATABASE DETAIL:
        {json.dumps(db_exploration.get('database_content', {}), indent=2, ensure_ascii=False)}

        PERTANYAAN USER: "{user_query}"

        INSTRUKSI FLEKSIBEL:
        1. PERTIMBANGAN AWAL: Pahami intent user - apakah mereka butuh data, penjelasan, bantuan teknis, atau sesuatu yang lain?
        2. ADAPTASI: Sesuaikan respons Anda dengan apa yang tersedia di database
        3. JIKA RELEVAN: Sarankan query SQL yang berguna (jika ada data yang sesuai)
        4. JIKA TIDAK RELEVAN: Berikan respons umum yang membantu tanpa data
        5. JIKA TIDAK PAHAM: Akui dengan jujur dan tawarkan bantuan alternatif
        6. SELALU: Bersikap helpful, informatif, dan natural

        JENIS PERTANYAAN & CONTOH RESPONS:

        PERTANYAAN TENTANG DATA:
        User: "berapa total penjualan?"
        AI: "Saya akan cek data penjualan Anda. [SQL: SELECT COUNT(*) FROM sales]"
        "Berdasarkan data, total penjualan adalah 150 transaksi."

         PERTANYAAN TENTANG STRUKTUR:
        User: "tabel apa saja yang ada?"
        AI: "Database Anda memiliki 3 tabel: products, customers, orders. Mau lihat data dari tabel mana?"

        PERTANYAAN BISNIS:
        User: "bagaimana performa bisnis?"
        AI: "Saya analisis data Anda. [SQL terkait] Berdasarkan data, revenue bulan ini Rp 50jt dengan 100 transaksi."

        PERTANYAAN TEKNIS:
        User: "cara query data customer?"
        AI: "Untuk melihat data customer, gunakan: SELECT * FROM customers LIMIT 10"

        PERTANYAAN UMUM:
        User: "halo"
        AI: "Halo! Saya siap membantu analisis database Anda. Ada yang bisa saya bantu?"

        PERTANYAAN TIDAK RELEVAN:
        User: "cuaca hari ini bagaimana?"
        AI: "Saya fokus membantu analisis database Anda. Untuk cuaca, mungkin butuh sumber lain. Ada yang bisa saya bantu terkait data Anda?"

        FORMAT RESPONS:
        - Natural conversation
        - Jelaskan apa yang Anda lakukan
        - Sertakan data jika ada
        - Tawarkan bantuan lanjutan
        - Jangan buat user bingung

        RESPONS ANDA:
        """
        
        return prompt
    
    def _extract_sql_query(self, ai_response: str) -> str:
        """Extract SQL query from AI response if present"""
        # Look for SQL in code blocks
        sql_match = re.search(r'```sql\s*(.*?)\s*```', ai_response, re.DOTALL)
        if sql_match:
            return sql_match.group(1).strip()
        
        # Look for SQL in square brackets
        sql_match = re.search(r'\[SQL:\s*(.*?)\]', ai_response)
        if sql_match:
            return sql_match.group(1).strip()
        
        return None
    
    async def _enhance_with_data(self, original_response: str, query_result: dict, user_query: str) -> str:
        """Enhance AI response with actual query results"""
        
        if not query_result.get('success'):
            return original_response
        
        data = query_result.get('data', [])
        if not data:
            return original_response + "\n\n Tidak ada data yang ditemukan dengan kriteria tersebut."
        
        prompt = f"""
        RESPONS ASLI AI: {original_response}
        
        HASIL DATA NYATA: {json.dumps(data, indent=2, ensure_ascii=False)}
        
        PERTANYAAN USER: "{user_query}"
        
        Tugas: Perbaiki respons AI dengan menyertakan data aktual yang didapat.
        Buat respons yang lebih informatif dan akurat berdasarkan data nyata.
        Pertahankan gaya conversational yang natural.
        
        RESPONS YANG DIPERBAIKI:
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error enhancing response with data: {e}")
            # Fallback: append basic data info
            return f"{original_response}\n\n Ditemukan {len(data)} record data."
    
    async def process_universal_chat(self, user_query: str, db_service: DatabaseService) -> dict:
        """Main method for flexible chat"""
        return await self.process_free_form_chat(user_query, db_service)
    
    async def process_chat_message(self, user_query: str, db_service: DatabaseService) -> dict:
        """Alias for compatibility"""
        return await self.process_free_form_chat(user_query, db_service)