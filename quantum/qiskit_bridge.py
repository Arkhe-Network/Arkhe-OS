import qiskit
from qiskit import QuantumCircuit, transpile
from qiskit_aer import Aer

def create_entanglement():
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure_all()
    simulator = Aer.get_backend("aer_simulator")
    compiled_circuit = transpile(qc, simulator)
    job = simulator.run(compiled_circuit, shots=1000)
    result = job.result()
    counts = result.get_counts(qc)
    return counts

if __name__ == "__main__":
    counts = create_entanglement()
    print("Quantum entanglement results:", counts)
