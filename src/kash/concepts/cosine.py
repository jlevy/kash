from collections.abc import Sequence

import numpy as np

# Type aliases for clarity
ArrayLike = Sequence[float] | np.ndarray


def cosine(u: ArrayLike, v: ArrayLike) -> float:
    """
    Compute the cosine distance between two 1-D arrays.
    Could use scipy.spatial.distance.cosine, but avoiding the dependency.
    """
    # Convert to numpy arrays
    u_array = np.asarray(u, dtype=np.float64)
    v_array = np.asarray(v, dtype=np.float64)

    # Verify vectors have same length
    if u_array.shape != v_array.shape:
        raise ValueError("The vectors must have the same dimensions")

    # Calculate norms
    norm_u = np.linalg.norm(u_array)
    norm_v = np.linalg.norm(v_array)

    # Handle zero norms
    if norm_u == 0 or norm_v == 0:
        # If both vectors are zero, consider them identical (zero distance)
        if norm_u == 0 and norm_v == 0:
            return 0.0
        # Otherwise one vector is zero and the other isn't (maximum distance)
        return 1.0  # Maximum distance when one vector is zero

    # Calculate dot product
    dot_product = np.dot(u_array, v_array)
    # Calculate cosine similarity
    similarity = dot_product / (norm_u * norm_v)
    # Calculate cosine distance and clip for numerical stability
    # Note: SciPy returns NaN for zero norms, while this returns 1.0.
    return np.clip(1.0 - similarity, 0.0, 2.0)
