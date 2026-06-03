"""Initialize face registry — spec section 4.3: P001-P005 with FaceNet512 embeddings."""
import os
import json
import numpy as np

EMBEDDINGS_DIR = "ml/embeddings"
os.makedirs(EMBEDDINGS_DIR, exist_ok=True)

DIM = 512  # FaceNet512

# Spec face identity database — exact table from section 4.3
REGISTRY = {
    "P001": {"name": "Alice Mercer", "category": "Employee", "risk_level": "Low",
              "access_zones": "Lobby, Lab A, Server Room", "color": "green"},
    "P002": {"name": "Bob Henley", "category": "Employee", "risk_level": "Low",
              "access_zones": "Lobby, Lab A", "color": "green"},
    "P003": {"name": "Carol Zhang", "category": "Visitor", "risk_level": "Medium",
              "access_zones": "Lobby only", "color": "amber"},
    "P004": {"name": "Dave Rostov", "category": "Suspect", "risk_level": "High",
              "access_zones": "NONE — flagged", "color": "red"},
    "P005": {"name": "Unknown", "category": "Unknown", "risk_level": "High",
              "access_zones": "NONE", "color": "red"},
}


def generate_realistic_embedding(person_id: str, seed: int) -> np.ndarray:
    """
    Generate synthetic but consistent FaceNet512-style embedding.
    Uses deterministic seed so embeddings are reproducible.
    In production these would come from DeepFace.represent().
    """
    rng = np.random.default_rng(seed)
    # FaceNet512 embeddings follow roughly normal distribution after L2 norm
    emb = rng.standard_normal(DIM).astype(np.float32)
    # L2 normalize (required for cosine similarity via FAISS IndexFlatIP)
    norm = np.linalg.norm(emb)
    if norm > 0:
        emb = emb / norm
    return emb


print("🎭 Initializing face registry (P001-P005)...")
print("=" * 50)

registry_meta = []
for i, (pid, info) in enumerate(REGISTRY.items()):
    emb = generate_realistic_embedding(pid, seed=42 + i * 100)
    emb_path = os.path.join(EMBEDDINGS_DIR, f"{pid}.npy")
    np.save(emb_path, emb)

    meta = {
        "person_id": pid,
        "name": info["name"],
        "category": info["category"],
        "risk_level": info["risk_level"],
        "access_zones": info["access_zones"],
        "embedding_path": emb_path,
        "embedding_dim": DIM,
        "model": "FaceNet512_synthetic",
    }
    registry_meta.append(meta)

    badge = "🟢" if info["risk_level"] == "Low" else "🟡" if info["risk_level"] == "Medium" else "🔴"
    print(f"  {badge} {pid}: {info['name']} | {info['category']} | Risk: {info['risk_level']}")

# Save registry index
registry_path = os.path.join(EMBEDDINGS_DIR, "registry.json")
with open(registry_path, "w") as f:
    json.dump(registry_meta, f, indent=2)

print("=" * 50)
print(f"✅ {len(REGISTRY)} embeddings saved to {EMBEDDINGS_DIR}/")
print(f"✅ Registry index: {registry_path}")
print()
print("Thresholds (spec section 7):")
print("  ≥ 0.82 cosine similarity → Positive match")
print("  0.60-0.82                → Tentative match")
print("  < 0.60                   → UNKNOWN")
