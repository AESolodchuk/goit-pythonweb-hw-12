import cloudinary
import cloudinary.uploader


class UploadFileService:
    """Upload user avatars to Cloudinary."""

    def __init__(self, cloud_name, api_key, api_secret):
        """Configure Cloudinary credentials for avatar uploads."""
        self.cloud_name = cloud_name
        self.api_key = api_key
        self.api_secret = api_secret
        cloudinary.config(
            cloud_name=self.cloud_name,
            api_key=self.api_key,
            api_secret=self.api_secret,
            secure=True,
        )

    @staticmethod
    def upload_file(file, username) -> str:
        """Upload an avatar and return its transformed public URL."""
        public_id = f"RestApp/{username}"
        r = cloudinary.uploader.upload(file.file, public_id=public_id, overwrite=True)
        src_url = cloudinary.CloudinaryImage(public_id).build_url(
            width=250, height=250, crop="fill", version=r.get("version")
        )
        return src_url
