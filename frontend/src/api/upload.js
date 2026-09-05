import axios from 'axios';
import client from './client.js';

const unwrap = (p) => p.then((r) => r.data);

// Step 1 of the presigned flow (spec section 15):
// GET /api/v1/upload/presigned -> { url | upload_url | presigned_url, source_id, fields? }
export function getPresignedUrl({ filename, contentType, sourceType }) {
  return unwrap(
    client.get('/upload/presigned', {
      params: {
        filename,
        content_type: contentType,
        source_type: sourceType,
      },
    }),
  );
}

// Legacy direct multipart upload fallback (spec section 8: POST /api/v1/upload).
export function uploadDirect(file, onUploadProgress) {
  const form = new FormData();
  form.append('file', file);
  return unwrap(
    client.post('/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress,
    }),
  );
}

// Step 2: PUT the file directly to MinIO using the presigned URL.
// Handles both plain PUT URLs and S3-style POST forms (with `fields`).
export async function uploadToPresigned(file, presigned, onUploadProgress) {
  const url = presigned.url || presigned.upload_url || presigned.presigned_url;
  if (!url) throw new Error('Presigned response did not include a URL');

  if (presigned.fields && Object.keys(presigned.fields).length > 0) {
    const form = new FormData();
    Object.entries(presigned.fields).forEach(([k, v]) => form.append(k, v));
    form.append('file', file);
    await axios.post(url, form, { onUploadProgress });
  } else {
    await axios.put(url, file, {
      headers: { 'Content-Type': file.type || 'application/octet-stream' },
      onUploadProgress,
    });
  }
  return presigned.source_id || presigned.sourceId || null;
}
