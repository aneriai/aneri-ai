from groq import Groq
from typing import Dict, Any, List
from app.config import Config
from app.core.vector_store import VectorStore
from app.core.document_loader import DocumentProcessor
from app.utils.prompt_templates import get_system_prompt, get_contextual_prompt
import logging

logger = logging.getLogger(__name__)


class RAGEngine:
    """RAG engine using ChromaDB + Groq (Llama3)"""

    def __init__(self):
        logger.info("Initializing RAG Engine...")

        if not Config.GROQ_API_KEY or Config.GROQ_API_KEY == 'YOUR_GROQ_API_KEY_HERE':
            raise ValueError("GROQ_API_KEY is not set. Please add it to your .env file.")

        # Groq client
        self.client = Groq(api_key=Config.GROQ_API_KEY)
        logger.info(f"Groq client ready | model: {Config.LLM_MODEL}")

        # Vector store + document processor
        self.vector_store  = VectorStore()
        self.doc_processor = DocumentProcessor()

        # Load knowledge base
        self._initialize_knowledge_base()

    # ─────────────────────────────────────────────────────────────
    def _initialize_knowledge_base(self):
        """Load resume into ChromaDB if not already done."""
        try:
            stats = self.vector_store.get_collection_stats()
            logger.info(f"Vector store has {stats['count']} documents")

            if stats['count'] == 0:
                logger.info("No documents found — ingesting resume now...")
                chunks = self.doc_processor.load_resume()

                metadata = [
                    {
                        "source":    "resume",
                        "chunk_id":  i,
                        "type":      "professional_info",
                        "section":   self._detect_section(chunk)
                    }
                    for i, chunk in enumerate(chunks)
                ]

                self.vector_store.add_documents(chunks, metadata)
                logger.info(f"✅ Ingested {len(chunks)} chunks into ChromaDB")
            else:
                logger.info(f"✅ Knowledge base already loaded ({stats['count']} chunks)")

        except Exception as e:
            logger.error(f"Knowledge base init failed: {e}")
            raise

    # ─────────────────────────────────────────────────────────────
    def _detect_section(self, text: str) -> str:
        t = text.lower()
        if any(w in t for w in ['experience', 'work', 'internship', 'job', 'engineer']):
            return 'experience'
        if any(w in t for w in ['skill', 'python', 'pytorch', 'tensorflow', 'sql']):
            return 'skills'
        if any(w in t for w in ['project', 'built', 'developed', 'deployed']):
            return 'projects'
        if any(w in t for w in ['education', 'degree', 'university', 'college', 'cgpa', 'gpa']):
            return 'education'
        return 'general'

    # ─────────────────────────────────────────────────────────────
    def _is_project_query(self, query: str) -> bool:
        """Check if the query is asking about projects."""
        keywords = ['project', 'built', 'developed', 'portfolio', 'what have you made', 'show me your work', 'your applications', 'mediask', 'chatbot', 'recommendation', 'detection system', 'surveillance']
        return any(k in query.lower() for k in keywords)

    # ─────────────────────────────────────────────────────────────
    # Hardcoded project list extracted from resume — prevents hallucination
    PROJECTS_CONTEXT = """
Project: AI Based Quality Inspection System
Company: Maharshi Industries Pvt. Ltd.
Description: Engineered AI-driven quality inspection solutions using RF-DETR and Qwen 3 8B Vision-Language Model (VLM). Detects 50+ defect parameters for industrial quality control and monitoring applications. Deployed for real-time production line inspection.
Tech Stack: RF-DETR | Qwen 3 8B VLM | PyTorch | OpenCV | Python

---

Project: AI Surveillance & Security System (DivyaChakshu AI)
Company: Maharshi Industries Pvt. Ltd.
Description: Developed a real-time surveillance and security system for defense applications including the Indian Army. Supports human, vehicle, helicopter, and animal detection for border surveillance near PoK using RGB and thermal imagery. Includes object detection, facial recognition, ANPR, and multi-camera video analytics.
Tech Stack: PyTorch | OpenCV | YOLOv8 | YOLOv11 | Thermal Imaging | Python

---

Project: Color Change Detection System
Company: Maharshi Industries Pvt. Ltd. (for DRDE Gwalior)
Description: Built an AI-based color change detection system for DRDE Gwalior to automate chemical resistance testing. The system uses computer vision and robotic integration to detect color changes, eliminating the need for manual testing and enabling remote contactless inspection.
Tech Stack: OpenCV | Python | Computer Vision | Robot Vision | Image Processing

---

Project: Rooftop Detection on Satellite Imagery
Company: BISAG-N (Bhaskaracharya National Institute for Space Applications)
Description: Developed a rooftop detection system on satellite imagery using multiple segmentation architectures. Annotated data in Roboflow (COCO & YOLO formats) for precise rooftop segmentation, supporting urban planning and geospatial analysis. Integrated QGIS for geospatial workflows.
Tech Stack: YOLOv8s-seg | YOLOv11s-seg | DeepLabV3+ (ResNet50) | U-Net (ResNet50) | Roboflow | QGIS | Python

---

Project: Tree Detection using Deep Learning
Company: BISAG-N (Bhaskaracharya National Institute for Space Applications)
Description: Built a tree detection and instance segmentation tool using UAV and satellite imagery. Annotated data in Roboflow (COCO & YOLO formats) for exact tree mapping. Incorporated QGIS for geospatial analysis, enabling canopy-based tree counting for environmental and forestry applications.
Tech Stack: YOLOv8-seg | YOLOv11-seg | Mask R-CNN | QGIS | Roboflow | Python

---

Project: Ask ANERI – AI Health & Skincare Chatbot
Company: Personal Project
Description: Developed an AI-powered health and skincare chatbot using Retrieval-Augmented Generation (RAG), LangChain, ChromaDB, and Large Language Models (LLMs). The chatbot answers questions on health, skincare, and women's wellness using a custom curated knowledge base.
Tech Stack: RAG | LangChain | ChromaDB | LLMs | Python | Flask

---

Project: Collaborative Filtering Recommendation System
Company: Personal Project
Description: Built a movie recommendation system using similarity-based collaborative filtering and machine learning techniques to identify relationships between users and items. Designed a user-friendly system to improve accessibility and personalized recommendations.
Tech Stack: Python | Machine Learning | Collaborative Filtering | Data Science

---

Project: MediASK – Medical AI Chatbot
Company: Personal Project
Description: Built a system to predict Trauma and cancer using brain and cell images via deep learning models. The system tells which disease a particular patient has based on symptoms and medical imaging, and includes a chatbot that answers questions related to medical problems.
Tech Stack: Deep Learning | Computer Vision | Medical AI | Python | Chatbot
"""

    def generate_response(self, query: str) -> Dict[str, Any]:
        """Retrieve context and call Groq to generate a response."""
        try:
            logger.info(f"Query: {query}")

            import time
            start_time = time.time()

            is_project = self._is_project_query(query)

            # For project queries: use the hardcoded structured project list to avoid hallucination
            if is_project:
                context = self.PROJECTS_CONTEXT
                sources = []
            else:
                # 1. Retrieve relevant chunks
                search_start = time.time()
                relevant_docs = self.vector_store.similarity_search(query, k=3)  # 3 is faster than 5
                logger.info(f"Similarity search took {time.time() - search_start:.4f} seconds")

                if not relevant_docs:
                    return {
                        'query':        query,
                        'response':     "I don't have that information in my knowledge base. Please ask something about Aneri's professional background.",
                        'sources':      [],
                        'context_used': False
                    }

                context = "\n\n".join([doc['text'] for doc in relevant_docs])

                sources = [
                    {
                        'text':    doc['text'][:200] + '…',
                        'score':   round(doc['relevance_score'], 3),
                        'section': doc['metadata'].get('section', 'general')
                    }
                    for doc in relevant_docs
                ]

            # 3. Build messages for Groq
            system_prompt = get_system_prompt(is_project=is_project)
            user_prompt   = get_contextual_prompt(query, context, is_project=is_project)

            messages = [
                {"role": "system",  "content": system_prompt},
                {"role": "user",    "content": user_prompt}
            ]

            # 4. Call Groq API — higher token limit for project answers
            groq_start = time.time()
            max_tokens = 1600 if is_project else Config.MAX_TOKENS
            chat_completion = self.client.chat.completions.create(
                model       = Config.LLM_MODEL,
                messages    = messages,
                temperature = Config.TEMPERATURE,
                max_tokens  = max_tokens,
            )
            logger.info(f"Groq API call took {time.time() - groq_start:.4f} seconds")

            response_text = chat_completion.choices[0].message.content
            logger.info(f"Total generate_response execution took {time.time() - start_time:.4f} seconds")

            return {
                'query':        query,
                'response':     response_text,
                'sources':      sources,
                'context_used': True
            }

        except Exception as e:
            logger.error(f"RAG error: {e}")
            return {
                'query':        query,
                'response':     f"Sorry, I ran into an error: {str(e)}",
                'error':        str(e),
                'sources':      [],
                'context_used': False
            }