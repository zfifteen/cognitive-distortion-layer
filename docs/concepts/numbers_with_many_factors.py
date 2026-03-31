import math


def divisor_count(n):
    if n < 1:
        return 0
    count = 0
    for i in range(1, int(math.sqrt(n)) + 1):
        if n % i == 0:
            count += 1
            if i != n // i:
                count += 1
    return count


def kappa(n):
    if n <= 1:
        return 0.0
    d = divisor_count(n)
    return d * math.log(n) / math.exp(2)


def is_prime(n):
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True


def classify(k, threshold):
    return "prime" if k < threshold else "composite"


def evaluate_range(start, end, threshold, sliding=False):
    primes = []
    composites = []
    correct_primes = 0
    correct_composites = 0
    total_primes = 0
    total_composites = 0

    for n in range(start, end + 1):
        k = kappa(n)
        pred = classify(
            k, threshold + (math.log(math.log(n)) if sliding and n > 1 else 0)
        )
        actual = "prime" if is_prime(n) else "composite"

        if actual == "prime":
            total_primes += 1
            if pred == actual:
                correct_primes += 1
            primes.append((n, k))
        else:
            total_composites += 1
            if pred == actual:
                correct_composites += 1
            composites.append((n, k))

    accuracy = (
        (correct_primes + correct_composites) / (total_primes + total_composites)
        if total_primes + total_composites > 0
        else 0
    )
    recall_primes = correct_primes / total_primes if total_primes > 0 else 0

    print(f"Range {start}-{end}:")
    print(
        f"  Avg prime kappa: {sum(k for _, k in primes) / len(primes) if primes else 0:.3f}"
    )
    print(
        f"  Avg composite kappa: {sum(k for _, k in composites) / len(composites) if composites else 0:.3f}"
    )
    print(f"  Accuracy: {accuracy:.3%}")
    print(f"  Prime recall: {recall_primes:.3%}")
    print()


if __name__ == "__main__":
    fixed_threshold = 1.5

    print("Demonstrating with fixed threshold (1.5):")
    evaluate_range(2, 50, fixed_threshold)
    evaluate_range(1000, 1050, fixed_threshold)

    print("Demonstrating with sliding threshold (1.5 + log(log(n))):")
    evaluate_range(2, 50, fixed_threshold, sliding=True)
    evaluate_range(1000, 1050, fixed_threshold, sliding=True)
