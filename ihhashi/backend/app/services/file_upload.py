"""
File upload service using Supabase Storage.
"""
import os
from typing import Optional, BinaryIO, List
from datetime import datetime
import uuid
from supabase import create_client, Client


class FileUploadService:
    """Service for uploading files to Supabase Storage."""
    
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_KEY")  # Service key for admin operations
        self.bucket_name = os.getenv("SUPABASE_STORAGE_BUCKET", "ihhashi-uploads")
        
        if self.supabase_url and self.supabase_key:
            self.client: Client = create_client(self.supabase_url, self.supabase_key)
        else:
            self.client = None
    
    def _generate_file_path(self, folder: str, filename: str, user_id: Optional[str] = None) -> str:
        """Generate a unique file path."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        ext = os.path.splitext(filename)[1]
        
        if user_id:
            return f"{folder}/{user_id}/{timestamp}_{unique_id}{ext}"
        return f"{folder}/{timestamp}_{unique_id}{ext}"
    
    async def upload_file(
        self,
        file: BinaryIO,
        filename: str,
        folder: str = "general",
        user_id: Optional[str] = None,
        content_type: Optional[str] = None
    ) -> dict:
        """
        Upload a file to Supabase Storage.
        
        Args:
            file: File-like object
            filename: Original filename
            folder: Folder to store in (profile-pics, delivery-photos, documents)
            user_id: Optional user ID for organized storage
            content_type: MIME type of the file
            
        Returns:
            dict with file_path and public_url
        """
        if not self.client:
            raise RuntimeError("Supabase client not configured")
        
        file_path = self._generate_file_path(folder, filename, user_id)
        file_content = file.read()
        
        options = {}
        if content_type:
            options["content-type"] = content_type
        
        response = self.client.storage.from_(self.bucket_name).upload(
            file_path,
            file_content,
            options
        )
        
        if response.get("error"):
            raise Exception(f"Upload failed: {response['error']['message']}")
        
        # Get public URL
        public_url = self.client.storage.from_(self.bucket_name).get_public_url(file_path)
        
        return {
            "file_path": file_path,
            "public_url": public_url,
            "filename": filename
        }
    
    async def upload_profile_picture(
        self,
        file: BinaryIO,
        filename: str,
        user_id: str
    ) -> dict:
        """Upload a user profile picture."""
        return await self.upload_file(
            file,
            filename,
            folder="profile-pics",
            user_id=user_id,
            content_type="image/jpeg"
        )
    
    async def upload_delivery_photo(
        self,
        file: BinaryIO,
        filename: str,
        delivery_id: str,
        user_id: str
    ) -> dict:
        """Upload a delivery-related photo."""
        file_path = self._generate_file_path(f"delivery-photos/{delivery_id}", filename, user_id)
        file_content = file.read()
        
        response = self.client.storage.from_(self.bucket_name).upload(
            file_path,
            file_content,
            {"content-type": "image/jpeg"}
        )
        
        if response.get("error"):
            raise Exception(f"Upload failed: {response['error']['message']}")
        
        public_url = self.client.storage.from_(self.bucket_name).get_public_url(file_path)
        
        return {
            "file_path": file_path,
            "public_url": public_url,
            "delivery_id": delivery_id
        }
    
    async def upload_document(
        self,
        file: BinaryIO,
        filename: str,
        doc_type: str,
        user_id: str
    ) -> dict:
        """
        Upload a document (ID, license, etc.).
        
        Args:
            doc_type: Type of document (id_document, driver_license, proof_of_address)
        """
        return await self.upload_file(
            file,
            filename,
            folder=f"documents/{doc_type}",
            user_id=user_id
        )
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete a file from storage."""
        if not self.client:
            raise RuntimeError("Supabase client not configured")
        
        response = self.client.storage.from_(self.bucket_name).remove([file_path])
        
        if response.get("error"):
            return False
        return True
    
    async def list_files(self, folder: str, user_id: Optional[str] = None) -> List[dict]:
        """List files in a folder."""
        if not self.client:
            raise RuntimeError("Supabase client not configured")
        
        path = f"{folder}/{user_id}" if user_id else folder
        
        response = self.client.storage.from_(self.bucket_name).list(path)
        
        if response.get("error"):
            return []
        
        return response.get("data", [])
    
    def get_public_url(self, file_path: str) -> str:
        """Get the public URL for a file."""
        if not self.client:
            raise RuntimeError("Supabase client not configured")
        
        return self.client.storage.from_(self.bucket_name).get_public_url(file_path)


# Global instance
_file_upload_service: Optional[FileUploadService] = None


def get_file_upload_service() -> FileUploadService:
    """Get the global file upload service instance."""
    global _file_upload_service
    if _file_upload_service is None:
        _file_upload_service = FileUploadService()
    return _file_upload_service
