import os
import random
import matplotlib.pyplot as plt

OUTPUT_DIR = 'plots_out'  # you can set any path here

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def main():
    ensure_dir(OUTPUT_DIR)

    data = [random.randint(1, 100) for _ in range(200)]

    # Line plot
    plt.figure(figsize=(10, 4))
    plt.plot(range(1, 201), data, marker='o', linestyle='-', color='tab:blue')
    plt.title('Line Plot of 200 Random Numbers (1-100)')
    plt.xlabel('Index')
    plt.ylabel('Value')
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'line_plot.png'))
    plt.close()

    # Histogram
    plt.figure(figsize=(6, 4))
    plt.hist(data, bins=range(0, 102, 2), edgecolor='black')
    plt.title('Histogram of 200 Random Numbers (1-100)')
    plt.xlabel('Value')
    plt.ylabel('Frequency')
    plt.xticks(range(0, 101, 10))
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'histogram.png'))
    plt.close()

if __name__ == '__main__':
    main()