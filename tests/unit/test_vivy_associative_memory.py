import numpy as np
from vivy.core.associative_memory import QuantumAssociativeMemory

def test_memory_initialization():
    mem = QuantumAssociativeMemory(dim=4)
    assert mem.dim == 4
    assert mem.W.shape == (4, 4)

def test_store_and_query():
    mem = QuantumAssociativeMemory(dim=4, use_unitary=True)
    # Define a simple basis state x and target y
    x = np.array([1.0, 0.0, 0.0, 0.0], dtype=complex)
    y = np.array([0.0, 1.0, 0.0, 0.0], dtype=complex)
    
    mem.store(x, y, eta=1.0)
    
    y_out, conf = mem.query(x)
    # The output should be close to y
    np.testing.assert_allclose(y_out, y, atol=1e-5)
    assert conf > 0.0

def test_memory_unitarization():
    mem = QuantumAssociativeMemory(dim=2, use_unitary=True)
    x = np.array([1.0, 0.0], dtype=complex)
    y = np.array([0.0, 1.0], dtype=complex)
    mem.store(x, y)
    
    # Check if W is approximately unitary (W @ W^H approx I)
    W_unitary_check = mem.W @ mem.W.conj().T
    # Note: If we only store one pattern in a larger space, the unitary matrix 
    # constructed via SVD polar decomposition will have singular values of 1.
    U, S, Vh = np.linalg.svd(mem.W)
    np.testing.assert_allclose(S, np.ones_like(S), atol=1e-5)
