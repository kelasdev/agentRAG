# Memahami Dimensi Vektor di Qdrant

Dalam konteks **Qdrant** (dan *vector database* pada umumnya), **dimensi** merujuk pada jumlah angka atau nilai numerik yang membentuk satu buah vektor.

Sederhananya, jika Anda membayangkan vektor sebagai sebuah titik di ruang koordinat, dimensi adalah jumlah sumbu yang menentukan posisi titik tersebut.

---

## 1. Vektor sebagai "Array" Angka

Vektor direpresentasikan sebagai sebuah daftar angka (array). Dimensi adalah **panjang** dari daftar tersebut.

* **Vektor 3-dimensi:** `[0.1, -0.5, 0.8]` (Ukuran dimensi = 3)
* **Vektor 5-dimensi:** `[1.2, 0.3, -0.9, 0.5, 0.1]` (Ukuran dimensi = 5)

## 2. Mengapa Dimensi Sangat Penting di Qdrant?

Saat Anda membuat sebuah *Collection* di Qdrant, Anda **wajib** menentukan ukuran dimensi. Hal ini karena:

* **Konsistensi:** Semua vektor yang dimasukkan ke dalam satu *collection* harus memiliki jumlah dimensi yang sama. Anda tidak bisa memasukkan vektor 128-dimensi ke dalam *collection* yang dikonfigurasi untuk 768-dimensi.
* **Operasi Matematika:** Qdrant melakukan perhitungan jarak (seperti *Cosine Similarity* atau *Euclidean Distance*) antar vektor. Perhitungan ini hanya bisa dilakukan jika kedua vektor memiliki panjang yang identik.

## 3. Dari Mana Angka Dimensi Ini Berasal?

Ukuran dimensi tidak ditentukan secara asal, melainkan bergantung pada **Embedding Model** yang Anda gunakan:

| Model Embedding | Ukuran Dimensi | Penggunaan Umum |
| --- | --- | --- |
| **OpenAI `text-embedding-3-small`** | 1536 | NLP / Chatbot |
| **HuggingFace `all-MiniLM-L6-v2`** | 384 | Ringan / Cepat |
| **Cohere `embed-multilingual-v3.0`** | 1024 | Pencarian Multibahasa |
| **FastEmbed `jinaai/jina-embeddings-v2-base-code`** | 768 | Code + Text (agentRAG default) |
| **ResNet-50 (Image)** | 2048 | Pengenalan Gambar |

---

## 4. Analogi Visual

Bayangkan Anda ingin mendeskripsikan sebuah "Apel" menggunakan angka:

1. **Dimensi 1 (Warna):** `[0.9]` (Sangat Merah)
2. **Dimensi 2 (Ukuran):** `[0.9, 0.2]` (Merah, Kecil)
3. **Dimensi 3 (Rasa):** `[0.9, 0.2, 0.8]` (Merah, Kecil, Manis)

Semakin banyak dimensi, semakin detail AI bisa "memahami" karakteristik objek tersebut, namun semakin besar pula memori RAM yang dibutuhkan oleh Qdrant.

---

## 5. Contoh Konfigurasi di Qdrant (Python)

Jika Anda menggunakan model dengan 768 dimensi, konfigurasinya akan terlihat seperti ini:

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

client = QdrantClient(":memory:")

client.create_collection(
    collection_name="my_collection",
    vectors_config=VectorParams(
        size=768,  # Ini adalah ukuran dimensinya
        distance=Distance.COSINE
    ),
)
```

**Poin Penting:** Pastikan nilai `size` pada Qdrant sama persis dengan output dari model AI yang Anda gunakan untuk menghasilkan *embedding*.

---

## 6. Dimensi di agentRAG

agentRAG secara otomatis mendeteksi dimensi dari embedding model yang Anda pilih:

### Default Configuration (FastEmbed)

```env
EMBEDDING_PROVIDER=fastembed
EMBEDDING_MODEL=jinaai/jina-embeddings-v2-base-code
```

**Dimensi:** 768

### Alternative: OpenAI-Compatible

```env
EMBEDDING_PROVIDER=openai_compatible
EMBEDDING_MODEL=text-embedding-3-small
OPENAI_COMPATIBLE_BASE_URL=https://api.openai.com/v1
OPENAI_COMPATIBLE_API_KEY=your_key
```

**Dimensi:** 1536

### Alternative: Llama.cpp (Local)

```env
EMBEDDING_PROVIDER=llama_cpp
LLAMA_CPP_EMBED_MODEL_PATH=/path/to/model.gguf
```

**Dimensi:** Tergantung model (biasanya 384-4096)

---

## 7. Troubleshooting: Dimension Mismatch

### Error yang Sering Muncul

```
Error: embedding dimension mismatch: 
  model_dim=768 
  collection_dim=1536 
  collection='agentrag_memory'
```

### Penyebab

1. **Ganti Model:** Anda mengganti embedding model tanpa membuat collection baru
2. **Salah Konfigurasi:** Collection dibuat dengan dimensi yang berbeda dari model

### Solusi

**Opsi 1: Buat Collection Baru**
```bash
# Ubah nama collection di .env
COLLECTION_NAME=agentrag_memory_v2
```

**Opsi 2: Hapus Collection Lama**
```python
from qdrant_client import QdrantClient

client = QdrantClient(url="your_url", api_key="your_key")
client.delete_collection("agentrag_memory")
```

**Opsi 3: Gunakan Model yang Sama**
```bash
# Pastikan model di .env sesuai dengan collection yang ada
```

---

## 8. Best Practices

### ✅ DO

- **Konsisten:** Gunakan satu embedding model untuk satu collection
- **Dokumentasi:** Catat model dan dimensi yang digunakan
- **Testing:** Test dengan `agentrag health` sebelum ingest besar-besaran
- **Naming:** Gunakan nama collection yang mencerminkan model (e.g., `agentrag_fastembed_768`)

### ❌ DON'T

- **Jangan** ganti model tanpa ganti collection
- **Jangan** hardcode dimensi tanpa cek model
- **Jangan** mix vektor dari model berbeda dalam satu collection

---

## 9. Referensi Lebih Lanjut

- [Qdrant Documentation - Collections](https://qdrant.tech/documentation/concepts/collections/)
- [Qdrant Documentation - Vectors](https://qdrant.tech/documentation/concepts/vectors/)
- [FastEmbed Models](https://qdrant.github.io/fastembed/examples/Supported_Models/)
- [OpenAI Embeddings Guide](https://platform.openai.com/docs/guides/embeddings)

---

## 10. Cek Dimensi di agentRAG

Gunakan command `health` untuk melihat konfigurasi dimensi:

```bash
agentrag health
```

Output:
```json
{
  "ok": true,
  "qdrant_ok": true,
  "embedder_ok": true,
  "collection_exists": true,
  "collection_points": 22,
  "collection_name": "agentrag_memory_fastembed",
  "embedding_provider": "fastembed",
  "embedding_dimensions": 768
}
```

Perhatikan field `embedding_dimensions` untuk memastikan dimensi sudah sesuai.
