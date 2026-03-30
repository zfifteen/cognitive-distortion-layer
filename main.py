import math
import numpy as np
import matplotlib.pyplot as plt
import csv
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split


class CognitiveModel:
    def __init__(self, cognitive_velocity=1.0, cognitive_coupling=1.0, load_factor=0.5):
        self.v_c = cognitive_velocity
        self.k = cognitive_coupling
        self.load_factor = load_factor

    def compute_cognitive_curvature(self, n):
        """Compute Zκ(n) = d(n)·ln(n)/e²"""
        if n < 2:
            return 0.0
        divisors = sum(1 if i * i == n else 2 for i in range(1, int(math.sqrt(n)) + 1) if n % i == 0)
        return divisors * math.log(n) / (math.e ** 2)

    def subliminal_frame_shift(self, n, cognitive_load=0.0):
        """Compute Δs = k·v_c(1 + load)·Zκ(n)"""
        v_c_mod = self.v_c * (1 + cognitive_load * self.load_factor)
        return self.k * v_c_mod * self.compute_cognitive_curvature(n)

    def conscious_perception(self, n, cognitive_load=0.0):
        """Simulate conscious perception: n_conscious = 𝒵(n)·exp(Δs)"""
        delta_s = self.subliminal_frame_shift(n, cognitive_load)
        return n * math.exp(delta_s)

    def z_transform(self, perceived_n, cognitive_load=0.0):
        """Recover true invariant: 𝒵(n) = n_conscious / exp(Δs)"""
        delta_s = self.subliminal_frame_shift(perceived_n, cognitive_load)
        return perceived_n / math.exp(delta_s)

    def number_of_divisors(self, n):
        if n < 2:
            return 0
        return sum(1 if i * i == n else 2 for i in range(1, int(math.sqrt(n)) + 1) if n % i == 0)

    def is_prime(self, n):
        return self.number_of_divisors(n) == 2


def simulate_cognitive_experiment(model, n_values, cognitive_load=0.0):
    results = []
    for n in n_values:
        true_invariant = model.z_transform(n, cognitive_load)
        perceived = model.conscious_perception(n, cognitive_load)
        distortion = perceived - n
        curvature = model.compute_cognitive_curvature(n)
        results.append((n, true_invariant, perceived, distortion, curvature))
    return results


def plot_perceptual_distortion(results, model):
    n_vals = [r[0] for r in results]
    true_vals = [r[1] for r in results]
    perceived_vals = [r[2] for r in results]
    curvature_vals = [r[4] for r in results]

    plt.figure(figsize=(14, 6))

    # Perception plot
    plt.subplot(1, 2, 1)
    plt.plot(n_vals, n_vals, 'g--', label="Ideal Perception")
    plt.plot(n_vals, true_vals, 'b-', linewidth=2, label="True Invariant 𝒵(n)")
    plt.plot(n_vals, perceived_vals, 'r-', label="Conscious Perception")
    primes = [n for n in n_vals if model.is_prime(n)]
    plt.scatter(primes, [r[2] for r in results if r[0] in primes],
                c='purple', s=50, label="Primes")
    plt.xlabel("Actual Number (n)")
    plt.ylabel("Perceived Value")
    plt.title("Cognitive Distortion in Numerical Perception")
    plt.legend()
    plt.grid(True)

    # Curvature plot
    plt.subplot(1, 2, 2)
    plt.plot(n_vals, curvature_vals, 'm-', label="Zκ(n) Curvature")
    plt.xlabel("Number (n)")
    plt.ylabel("Cognitive Curvature")
    plt.title("Numerical Curvature Across Numberspace")
    plt.legend()
    plt.grid(True)

    plt.tight_layout()
    plt.show()


def export_results_to_csv(results, filename="cognitive_results.csv"):
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["n", "Z(n)", "Perceived", "Distortion", "Curvature"])
        for row in results:
            writer.writerow(row)


def ai_validation_experiment(model, max_n=1000):
    X_raw = np.array([[n, model.compute_cognitive_curvature(n)] for n in range(2, max_n)])
    y = np.array([1 if model.is_prime(n) else 0 for n in range(2, max_n)])

    X_transformed = np.array([[model.z_transform(n), model.compute_cognitive_curvature(n)]
                              for n in range(2, max_n)])

    X_train, X_test, y_train, y_test = train_test_split(X_raw, y, test_size=0.2)
    Xt_train, Xt_test, _, _ = train_test_split(X_transformed, y, test_size=0.2)

    model_raw = RandomForestClassifier().fit(X_train, y_train)
    model_transformed = RandomForestClassifier().fit(Xt_train, y_train)

    raw_score = model_raw.score(X_test, y_test)
    trans_score = model_transformed.score(Xt_test, y_test)

    return raw_score, trans_score


# Main execution
if __name__ == "__main__":
    model = CognitiveModel()
    numbers = range(2, 51)
    load_levels = [0.0, 0.3, 0.7]

    for load in load_levels:
        print(f"\n=== Cognitive Frame Shift Simulation (Load: {load:.1f}) ===")
        print("n | True 𝒵(n) | Perceived | Distortion | Curvature")
        print("-" * 60)
        results = simulate_cognitive_experiment(model, numbers, cognitive_load=load)
        for n, true, perceived, distortion, curvature in results:
            print(f"{n:2} | {true:8.4f} | {perceived:10.4f} | {distortion:+.4f} | {curvature:.4f}")
        plot_perceptual_distortion(results, model)
        export_results_to_csv(results, filename=f"results_load_{int(load*100)}.csv")

    raw_acc, trans_acc = ai_validation_experiment(model, max_n=1000)
    print(f"\n=== AI Validation ===")
    print(f"Raw Accuracy: {raw_acc:.4f}")
    print(f"Z-Transformed Accuracy: {trans_acc:.4f}")
    print(f"Improvement: {(trans_acc - raw_acc) * 100:.2f}%")
