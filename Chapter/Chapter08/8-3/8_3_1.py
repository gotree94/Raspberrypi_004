import torch

MODEL_PATH = "model-20260714_231443\\lane_navigation_final.torchscript"

def main():
    model = torch.jit.load(MODEL_PATH, map_location="cpu")
    model.eval()
    torch.set_num_threads(1)
    x = torch.zeros(1, 3, 66, 200, dtype=torch.float32)
    with torch.no_grad():
        y = model(x)
    print('model_loaded:', type(model).__name__)
    print("dry_run_output: ", float(y.view(-1)[0].item()))

if __name__ == "__main__":
    main()