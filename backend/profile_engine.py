"""
Profile Ingestion Engine for AutoCareer.
Parses resumes, extracts information, and creates vector embeddings.
"""

import os
import re
from typing import Dict, List, Optional, Tuple
import pdfplumber
from sentence_transformers import SentenceTransformer
import numpy as np
import pickle
from database import get_db


class ProfileEngine:
    """Resume parser and vector embedding generator."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize with sentence transformer model."""
        self.model = SentenceTransformer(model_name)
        self.vector_store_path = "./backend/data/vectors.pkl"
        self.vectors = self._load_vectors()
        
    def _load_vectors(self) -> Dict:
        """Load existing vector store or create new one."""
        if os.path.exists(self.vector_store_path):
            with open(self.vector_store_path, 'rb') as f:
                return pickle.load(f)
        return {"embeddings": [], "metadata": [], "texts": []}
    
    def _save_vectors(self):
        """Save vector store to disk."""
        os.makedirs(os.path.dirname(self.vector_store_path), exist_ok=True)
        with open(self.vector_store_path, 'wb') as f:
            pickle.dump(self.vectors, f)
    
    def parse_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF resume."""
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text
    
    def extract_sections(self, text: str) -> Dict[str, str]:
        """
        Extract structured sections from resume text.
        Returns: name, email, phone, skills, experience, education, links
        """
        sections = {
            "name": "",
            "email": "",
            "phone": "",
            "skills": "",
            "experience": "",
            "education": "",
            "links": ""
        }
        
        # Extract email
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        if email_match:
            sections["email"] = email_match.group(0)
        
        # Extract phone
        phone_match = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
        if phone_match:
            sections["phone"] = phone_match.group(0)
        
        # Extract name (assume first line or before contact info)
        lines = text.split('\n')
        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            if line and len(line.split()) <= 4 and not '@' in line and not any(char.isdigit() for char in line):
                sections["name"] = line
                break
        
        # Extract links (GitHub, LinkedIn, portfolio)
        links = re.findall(r'(https?://[^\s]+|www\.[^\s]+|github\.com/[^\s]+|linkedin\.com/in/[^\s]+)', text, re.IGNORECASE)
        sections["links"] = ", ".join(links) if links else ""
        
        # Section keywords
        text_lower = text.lower()
        
        # Extract skills
        skills_start = max(
            text_lower.find('skills'),
            text_lower.find('technical skills'),
            text_lower.find('core competencies')
        )
        if skills_start != -1:
            skills_end = min(
                text_lower.find('experience', skills_start),
                text_lower.find('education', skills_start),
                text_lower.find('projects', skills_start),
                len(text)
            )
            sections["skills"] = text[skills_start:skills_end].strip()
        
        # Extract experience
        exp_start = max(
            text_lower.find('experience'),
            text_lower.find('work experience'),
            text_lower.find('employment')
        )
        if exp_start != -1:
            exp_end = min(
                text_lower.find('education', exp_start),
                text_lower.find('projects', exp_start),
                len(text)
            )
            sections["experience"] = text[exp_start:exp_end].strip()
        
        # Extract education
        edu_start = text_lower.find('education')
        if edu_start != -1:
            edu_end = min(
                text_lower.find('certifications', edu_start),
                text_lower.find('projects', edu_start),
                len(text)
            )
            sections["education"] = text[edu_start:edu_end].strip()
        
        return sections
    
    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Split text into overlapping chunks for embedding."""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk:
                chunks.append(chunk)
        
        return chunks
    
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for text chunks."""
        embeddings = self.model.encode(texts, show_progress_bar=False)
        return embeddings
    
    def ingest_resume(self, pdf_path: str, profile_id: Optional[int] = None) -> Tuple[int, str]:
        """
        Complete resume ingestion pipeline.
        Returns: (profile_id, vector_db_id)
        """
        db = get_db()
        
        # Parse PDF
        full_text = self.parse_pdf(pdf_path)
        
        # Extract sections
        sections = self.extract_sections(full_text)
        
        # Chunk text for embeddings
        chunks = self.chunk_text(full_text)
        
        # Generate embeddings
        embeddings = self.generate_embeddings(chunks)
        
        # Store in vector database
        vector_db_id = f"profile_{profile_id or 'default'}"
        
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            self.vectors["embeddings"].append(embedding)
            self.vectors["texts"].append(chunk)
            self.vectors["metadata"].append({
                "profile_id": profile_id,
                "chunk_id": i,
                "type": "resume_chunk"
            })
        
        self._save_vectors()
        
        # Store in database
        if not profile_id:
            profile_id = db.insert_profile(
                name=sections["name"] or "Unknown",
                email=sections["email"],
                resume_text=full_text,
                skills=sections["skills"],
                experience=sections["experience"],
                education=sections["education"],
                links=sections["links"],
                vector_db_id=vector_db_id
            )
        else:
            # Update existing profile
            db.cursor.execute("""
                UPDATE profiles 
                SET resume_text = ?, skills = ?, experience = ?, education = ?, 
                    links = ?, vector_db_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (full_text, sections["skills"], sections["experience"], 
                  sections["education"], sections["links"], vector_db_id, profile_id))
            db.conn.commit()
        
        return profile_id, vector_db_id
    
    def search_similar(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search for similar content in vector store."""
        if not self.vectors["embeddings"]:
            return []
        
        query_embedding = self.model.encode([query])[0]
        embeddings_array = np.array(self.vectors["embeddings"])
        
        # Compute cosine similarity
        similarities = np.dot(embeddings_array, query_embedding) / (
            np.linalg.norm(embeddings_array, axis=1) * np.linalg.norm(query_embedding)
        )
        
        # Get top k
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            results.append({
                "text": self.vectors["texts"][idx],
                "similarity": float(similarities[idx]),
                "metadata": self.vectors["metadata"][idx]
            })
        
        return results
