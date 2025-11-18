# modules/telegraph_uploader.py
import asyncio
import logging
from html_telegraph_poster.poster import TelegraphPoster
from html_telegraph_poster.upload_images import upload_image

logger = logging.getLogger(__name__)


async def upload_image_to_graph(image_path: str) -> str:
    """
    एक इमेज फ़ाइल को graph.org पर अपलोड करता है।
    यह एक ब्लॉकिंग फ़ंक्शन है, इसलिए इसे thread में चलाते हैं।
    """
    try:
        # upload_image एक ब्लॉकिंग (sync) फ़ंक्शन है
        loop = asyncio.get_event_loop()
        url = await loop.run_in_executor(None, upload_image, image_path)
        logger.info(f"Image uploaded to graph: {url}")
        return url
    except Exception as e:
        logger.error(f"Graph image upload failed: {e}")
        return None


async def post_to_graph(title: str, html_content: str) -> str:
    """
    HTML कंटेंट को graph.org पर पोस्ट करता है।
    """
    try:
        # graph.org का इस्तेमाल करने के लिए API URL को ओवरराइड करें
        t = TelegraphPoster(use_api=True,
                            telegraph_api_url='https://api.graph.org')

        loop = asyncio.get_event_loop()

        # t.post() एक ब्लॉकिंग (sync) फ़ंक्शन है
        response = await loop.run_in_executor(
            None,
            t.post,
            title,
            'Unknown',  # Author name
            html_content)

        page_url = response['url']
        logger.info(f"Posted to graph.org: {page_url}")
        return page_url
    except Exception as e:
        logger.error(f"Graph post failed: {e}")
        return None
