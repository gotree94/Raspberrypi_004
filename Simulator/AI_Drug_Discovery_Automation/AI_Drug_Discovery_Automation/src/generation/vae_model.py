"""
SMILES VAE Model
=================
PyTorch 기반 Variational Autoencoder for de novo molecular generation.
Character-level RNN encoder/decoder with reparameterization trick.
"""

import re
import numpy as np
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

from src.config import get_config


# ──────────────────────────────────────────────────────────
# SMILES Tokenizer
# ──────────────────────────────────────────────────────────

CHARSET = (
    "C", "c", "N", "n", "O", "o", "S", "s", "P", "p", "F", "Cl", "Br",
    "I", "H", "B", "b", "Se", "Si",
    "(", ")", "[", "]", "{", "}", "=", "#", "@", "*", "%", "0",
    "1", "2", "3", "4", "5", "6", "7", "8", "9",
    "+", "-", "/", "\\", ":", "~", ".", "$", "^", "_", "?", "!",
    "<", ">", "|", "&", ";", "`",
)
MAX_LEN = 120


class SMILESTokenizer:
    """Character-level SMILES tokenizer."""

    def __init__(self, charset: Optional[List[str]] = None):
        self.charset = charset or CHARSET
        # Remove duplicates while preserving order
        self.charset = list(dict.fromkeys(self.charset))
        self._char_to_idx = {c: i + 2 for i, c in enumerate(self.charset)}  # 0=PAD, 1=EOS
        self._idx_to_char = {i + 2: c for i, c in enumerate(self.charset)}
        self._idx_to_char[0] = "<PAD>"
        self._idx_to_char[1] = "<EOS>"
        self.vocab_size = len(self.charset) + 2
        self.pad_idx = 0
        self.eos_idx = 1

    def encode(self, smiles: str, max_len: int = MAX_LEN) -> torch.Tensor:
        """Encode a SMILES string to a tensor of token indices."""
        tokens = list(smiles)
        indices = [self._char_to_idx.get(t, self.pad_idx) for t in tokens]
        indices = indices[:max_len - 1] + [self.eos_idx]
        # Pad to max_len
        indices += [self.pad_idx] * (max_len - len(indices))
        return torch.tensor(indices, dtype=torch.long)

    def decode(self, indices: torch.Tensor) -> str:
        """Decode a tensor of token indices to a SMILES string."""
        chars = []
        for i in indices.tolist():
            if i == self.eos_idx:
                break
            if i == self.pad_idx:
                continue
            chars.append(self._idx_to_char.get(i, "?"))
        return "".join(chars)

    def encode_batch(self, smiles_list: List[str], max_len: int = MAX_LEN) -> torch.Tensor:
        """Encode a list of SMILES strings to a batch tensor."""
        return torch.stack([self.encode(s, max_len) for s in smiles_list])

    def decode_batch(self, tensor: torch.Tensor) -> List[str]:
        """Decode a batch tensor to a list of SMILES strings."""
        return [self.decode(t) for t in tensor]

    @property
    def charset_size(self) -> int:
        return self.vocab_size


# ──────────────────────────────────────────────────────────
# SMILES Dataset
# ──────────────────────────────────────────────────────────


class SMILESDataset(Dataset):
    """PyTorch Dataset for SMILES strings."""

    def __init__(self, smiles_list: List[str], tokenizer: SMILESTokenizer, max_len: int = MAX_LEN):
        self.smiles_list = smiles_list
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self) -> int:
        return len(self.smiles_list)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        smiles = self.smiles_list[idx]
        tokens = self.tokenizer.encode(smiles, self.max_len)
        # For language modeling: input = tokens[:-1], target = tokens[1:]
        return tokens[:-1], tokens[1:]


# ──────────────────────────────────────────────────────────
# VAE Model
# ──────────────────────────────────────────────────────────


class Encoder(nn.Module):
    """GRU-based encoder that maps SMILES to latent distribution parameters."""

    def __init__(self, vocab_size: int, hidden_dim: int, latent_dim: int, num_layers: int = 2, dropout: float = 0.3):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, hidden_dim)
        self.gru = nn.GRU(
            hidden_dim, hidden_dim, num_layers=num_layers,
            batch_first=True, dropout=dropout if num_layers > 1 else 0,
            bidirectional=True,
        )
        self.fc_mu = nn.Linear(hidden_dim * 2, latent_dim)
        self.fc_logvar = nn.Linear(hidden_dim * 2, latent_dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        embedded = self.dropout(self.embedding(x))
        _, hidden = self.gru(embedded)
        # Concatenate the last layer's forward and backward hidden states
        hidden_combined = torch.cat((hidden[-2, :, :], hidden[-1, :, :]), dim=1)
        mu = self.fc_mu(hidden_combined)
        logvar = self.fc_logvar(hidden_combined)
        return mu, logvar


class Decoder(nn.Module):
    """GRU-based decoder that generates SMILES from latent vector."""

    def __init__(self, vocab_size: int, hidden_dim: int, latent_dim: int, num_layers: int = 2, dropout: float = 0.3):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, hidden_dim)
        self.latent_to_hidden = nn.Linear(latent_dim, num_layers * hidden_dim)
        self.gru = nn.GRU(
            hidden_dim, hidden_dim, num_layers=num_layers,
            batch_first=True, dropout=dropout if num_layers > 1 else 0,
        )
        self.fc_out = nn.Linear(hidden_dim, vocab_size)
        self.dropout = nn.Dropout(dropout)
        self.num_layers = num_layers
        self.hidden_dim = hidden_dim

    def forward(self, x: torch.Tensor, z: torch.Tensor, hidden: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, torch.Tensor]:
        if hidden is None:
            hidden = self.latent_to_hidden(z).view(-1, self.num_layers, self.hidden_dim).transpose(0, 1).contiguous()
        embedded = self.dropout(self.embedding(x))
        output, hidden = self.gru(embedded, hidden)
        logits = self.fc_out(output)
        return logits, hidden


class SMILESVAE(nn.Module):
    """
    Variational Autoencoder for SMILES generation.

    Architecture:
        - Character-level GRU encoder (bidirectional)
        - Latent space with reparameterization
        - GRU decoder conditioned on latent vector
    """

    def __init__(
        self,
        vocab_size: int,
        hidden_dim: int = 256,
        latent_dim: int = 128,
        num_layers: int = 2,
        dropout: float = 0.3,
        max_len: int = MAX_LEN,
    ):
        super().__init__()
        self.encoder = Encoder(vocab_size, hidden_dim, latent_dim, num_layers, dropout)
        self.decoder = Decoder(vocab_size, hidden_dim, latent_dim, num_layers, dropout)
        self.latent_dim = latent_dim
        self.max_len = max_len
        self.vocab_size = vocab_size

        # For computing KL annealing weight
        self.register_buffer("kl_weight", torch.tensor(1.0))

    def reparameterize(self, mu: torch.Tensor, logvar: torch.Tensor) -> torch.Tensor:
        """Reparameterization trick: z = mu + std * epsilon."""
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Forward pass.

        Args:
            x: Input tensor of token indices, shape (batch, seq_len)

        Returns:
            logits: Decoder output logits
            mu: Mean of latent distribution
            logvar: Log variance of latent distribution
        """
        mu, logvar = self.encoder(x)
        z = self.reparameterize(mu, logvar)
        # Teacher forcing: decoder input is original input shifted right
        # (first token is assumed to be a start token or we shift)
        decoder_input = x[:, :-1]
        logits, _ = self.decoder(decoder_input, z)
        return logits, mu, logvar

    def loss_function(
        self,
        logits: torch.Tensor,
        targets: torch.Tensor,
        mu: torch.Tensor,
        logvar: torch.Tensor,
        kl_weight: Optional[float] = None,
    ) -> Dict[str, torch.Tensor]:
        """
        Compute VAE loss = reconstruction loss + KL divergence.

        Args:
            logits: Decoder output logits (batch, seq_len-1, vocab_size)
            targets: Target token indices (batch, seq_len-1)
            mu: Mean of latent distribution
            logvar: Log variance of latent distribution
            kl_weight: Weight for KL divergence (for annealing)

        Returns:
            Dictionary with 'loss', 'recon_loss', 'kl_loss' keys
        """
        kw = kl_weight if kl_weight is not None else self.kl_weight

        # Reconstruction loss (cross-entropy, ignoring padding)
        recon_loss = F.cross_entropy(
            logits.reshape(-1, self.vocab_size),
            targets.reshape(-1),
            ignore_index=0,  # PAD index
            reduction="mean",
        )

        # KL divergence
        kl_loss = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())
        kl_loss = kl_loss / targets.size(0)  # Normalize by batch size

        total_loss = recon_loss + kw * kl_loss
        return {"loss": total_loss, "recon_loss": recon_loss, "kl_loss": kl_loss}

    @torch.no_grad()
    def sample(self, num_samples: int = 1, temperature: float = 1.0, max_len: Optional[int] = None) -> torch.Tensor:
        """
        Sample new molecules from the latent space.

        Args:
            num_samples: Number of molecules to generate
            temperature: Sampling temperature (higher = more random)
            max_len: Maximum SMILES length

        Returns:
            Tensor of token indices, shape (num_samples, max_len)
        """
        self.eval()
        max_len = max_len or self.max_len
        device = next(self.parameters()).device
        z = torch.randn(num_samples, self.latent_dim, device=device)

        # Initialize decoder with latent vector
        hidden = self.decoder.latent_to_hidden(z).view(-1, self.decoder.num_layers, self.decoder.hidden_dim).transpose(0, 1).contiguous()

        # Start token (we use a simple heuristic: first char index)
        # In practice, the model learns to start from any token
        x = torch.full((num_samples, 1), 2, dtype=torch.long, device=device)  # Start with first charset token
        generated = [x]

        for _ in range(max_len - 1):
            embedded = self.decoder.dropout(self.decoder.embedding(x))
            output, hidden = self.decoder.gru(embedded, hidden)
            logits = self.decoder.fc_out(output[:, -1, :])  # (batch, vocab_size)

            # Apply temperature
            if temperature > 0:
                logits = logits / temperature

            probs = F.softmax(logits, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1)
            generated.append(next_token)
            x = next_token

        return torch.cat(generated, dim=1)

    @torch.no_grad()
    def reconstruct(self, smiles_tensor: torch.Tensor, temperature: float = 0.1) -> torch.Tensor:
        """
        Reconstruct SMILES from input through the VAE bottleneck.

        Args:
            smiles_tensor: Input SMILES tensor (batch, seq_len)
            temperature: Sampling temperature for reconstruction

        Returns:
            Reconstructed SMILES tensor
        """
        self.eval()
        mu, logvar = self.encoder(smiles_tensor)
        z = self.reparameterize(mu, logvar)
        return self.sample_from_z(z, temperature)

    @torch.no_grad()
    def sample_from_z(self, z: torch.Tensor, temperature: float = 1.0, max_len: Optional[int] = None) -> torch.Tensor:
        """Sample from a given latent vector z."""
        self.eval()
        max_len = max_len or self.max_len
        device = z.device
        num_samples = z.size(0)

        hidden = self.decoder.latent_to_hidden(z).view(-1, self.decoder.num_layers, self.decoder.hidden_dim).transpose(0, 1).contiguous()
        x = torch.full((num_samples, 1), 2, dtype=torch.long, device=device)
        generated = [x]

        for _ in range(max_len - 1):
            embedded = self.decoder.dropout(self.decoder.embedding(x))
            output, hidden = self.decoder.gru(embedded, hidden)
            logits = self.decoder.fc_out(output[:, -1, :])

            if temperature > 0:
                logits = logits / temperature

            probs = F.softmax(logits, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1)
            generated.append(next_token)
            x = next_token

        return torch.cat(generated, dim=1)

    def interpolate(self, smiles_a: str, smiles_b: str, tokenizer: SMILESTokenizer, steps: int = 10) -> List[str]:
        """
        Interpolate between two SMILES strings in latent space.

        Args:
            smiles_a: First SMILES
            smiles_b: Second SMILES
            tokenizer: SMILESTokenizer instance
            steps: Number of interpolation steps

        Returns:
            List of interpolated SMILES strings
        """
        self.eval()
        with torch.no_grad():
            tensor_a = tokenizer.encode(smiles_a, self.max_len).unsqueeze(0)
            tensor_b = tokenizer.encode(smiles_b, self.max_len).unsqueeze(0)

            mu_a, logvar_a = self.encoder(tensor_a)
            mu_b, logvar_b = self.encoder(tensor_b)
            z_a = self.reparameterize(mu_a, logvar_a)
            z_b = self.reparameterize(mu_b, logvar_b)

            results = []
            alphas = np.linspace(0, 1, steps)
            for alpha in alphas:
                z_interp = (1 - alpha) * z_a + alpha * z_b
                tokens = self.sample_from_z(z_interp, temperature=0.5)
                smiles = tokenizer.decode(tokens[0])
                results.append(smiles)
        return results


# ──────────────────────────────────────────────────────────
# VAE Trainer
# ──────────────────────────────────────────────────────────


class VAETrainer:
    """
    Trainer for SMILES VAE with KL annealing and early stopping.
    """

    def __init__(
        self,
        model: SMILESVAE,
        tokenizer: SMILESTokenizer,
        learning_rate: float = 1e-3,
        kl_anneal_start: int = 10,
        kl_anneal_end: int = 30,
        kl_max_weight: float = 1.0,
        device: Optional[str] = None,
    ):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)

        self.optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
        self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, mode="min", factor=0.5, patience=5, verbose=True
        )

        self.kl_anneal_start = kl_anneal_start
        self.kl_anneal_end = kl_anneal_end
        self.kl_max_weight = kl_max_weight
        self.history: Dict[str, List[float]] = {"loss": [], "recon_loss": [], "kl_loss": [], "kl_weight": []}
        self.best_loss = float("inf")
        self.patience_counter = 0
        self.early_stop_patience = 15

    def _get_kl_weight(self, epoch: int) -> float:
        """Compute KL annealing weight for the current epoch."""
        if epoch < self.kl_anneal_start:
            return 0.0
        elif epoch >= self.kl_anneal_end:
            return self.kl_max_weight
        else:
            progress = (epoch - self.kl_anneal_start) / (self.kl_anneal_end - self.kl_anneal_start)
            return self.kl_max_weight * progress

    def train_epoch(self, dataloader: DataLoader, kl_weight: float) -> Dict[str, float]:
        """Train for one epoch."""
        self.model.train()
        total_loss = 0.0
        total_recon = 0.0
        total_kl = 0.0
        num_batches = len(dataloader)

        for batch_idx, (inputs, targets) in enumerate(dataloader):
            inputs = inputs.to(self.device)
            targets = targets.to(self.device)

            self.optimizer.zero_grad()
            logits, mu, logvar = self.model(inputs)
            losses = self.model.loss_function(logits, targets, mu, logvar, kl_weight)

            losses["loss"].backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=5.0)
            self.optimizer.step()

            total_loss += losses["loss"].item()
            total_recon += losses["recon_loss"].item()
            total_kl += losses["kl_loss"].item()

        return {
            "loss": total_loss / num_batches,
            "recon_loss": total_recon / num_batches,
            "kl_loss": total_kl / num_batches,
        }

    @torch.no_grad()
    def evaluate(self, dataloader: DataLoader, kl_weight: float) -> Dict[str, float]:
        """Evaluate on validation set."""
        self.model.eval()
        total_loss = 0.0
        total_recon = 0.0
        total_kl = 0.0
        num_batches = len(dataloader)

        for inputs, targets in dataloader:
            inputs = inputs.to(self.device)
            targets = targets.to(self.device)
            logits, mu, logvar = self.model(inputs)
            losses = self.model.loss_function(logits, targets, mu, logvar, kl_weight)

            total_loss += losses["loss"].item()
            total_recon += losses["recon_loss"].item()
            total_kl += losses["kl_loss"].item()

        return {
            "loss": total_loss / num_batches,
            "recon_loss": total_recon / num_batches,
            "kl_loss": total_kl / num_batches,
        }

    def fit(
        self,
        train_dataset: SMILESDataset,
        val_dataset: Optional[SMILESDataset] = None,
        batch_size: int = 64,
        num_epochs: int = 100,
    ) -> Dict[str, List[float]]:
        """
        Full training loop with KL annealing and early stopping.

        Args:
            train_dataset: Training dataset
            val_dataset: Validation dataset (optional)
            batch_size: Batch size
            num_epochs: Maximum number of epochs

        Returns:
            Training history dictionary
        """
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False) if val_dataset else None

        for epoch in range(1, num_epochs + 1):
            kl_weight = self._get_kl_weight(epoch)

            train_metrics = self.train_epoch(train_loader, kl_weight)
            self.history["loss"].append(train_metrics["loss"])
            self.history["recon_loss"].append(train_metrics["recon_loss"])
            self.history["kl_loss"].append(train_metrics["kl_loss"])
            self.history["kl_weight"].append(kl_weight)

            # Validation
            if val_loader:
                val_metrics = self.evaluate(val_loader, kl_weight)
                self.scheduler.step(val_metrics["loss"])

                if val_metrics["loss"] < self.best_loss:
                    self.best_loss = val_metrics["loss"]
                    self.patience_counter = 0
                else:
                    self.patience_counter += 1

                if self.patience_counter >= self.early_stop_patience:
                    print(f"Early stopping at epoch {epoch}")
                    break

            # Logging
            if epoch % 10 == 0 or epoch == 1:
                print(f"Epoch {epoch:3d} | Loss: {train_metrics['loss']:.4f} | "
                      f"Recon: {train_metrics['recon_loss']:.4f} | "
                      f"KL: {train_metrics['kl_loss']:.4f} | "
                      f"KL_w: {kl_weight:.3f}")

        return self.history

    def save(self, path: str) -> None:
        """Save model checkpoint."""
        import json
        checkpoint = {
            "model_state_dict": self.model.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "history": self.history,
            "config": {
                "vocab_size": self.model.vocab_size,
                "hidden_dim": self.model.encoder.gru.hidden_size,
                "latent_dim": self.model.latent_dim,
                "max_len": self.model.max_len,
            },
        }
        torch.save(checkpoint, path)
        # Save tokenizer charset alongside
        import json
        charset_path = path.replace(".pt", "_charset.json")
        with open(charset_path, "w") as f:
            json.dump({"charset": self.tokenizer.charset}, f)

    @classmethod
    def load(cls, path: str, device: Optional[str] = None) -> "VAETrainer":
        """Load model checkpoint."""
        import json
        checkpoint = torch.load(path, map_location=device or "cpu")

        # Load charset
        charset_path = path.replace(".pt", "_charset.json")
        charset = None
        try:
            with open(charset_path) as f:
                data = json.load(f)
                charset = data.get("charset")
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        tokenizer = SMILESTokenizer(charset)
        config = checkpoint["config"]
        model = SMILESVAE(
            vocab_size=config["vocab_size"],
            hidden_dim=config["hidden_dim"],
            latent_dim=config["latent_dim"],
            max_len=config["max_len"],
        )
        model.load_state_dict(checkpoint["model_state_dict"])

        device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        trainer = cls(model, tokenizer, device=device)
        trainer.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        trainer.history = checkpoint.get("history", {})
        return trainer

    def generate_valid_smiles(self, num_attempts: int = 100, temperature: float = 1.0, max_len: Optional[int] = None) -> List[str]:
        """
        Generate SMILES strings and filter valid ones using RDKit.

        Args:
            num_attempts: Number of sampling attempts
            temperature: Sampling temperature
            max_len: Maximum SMILES length

        Returns:
            List of valid SMILES strings
        """
        try:
            from rdkit import Chem
        except ImportError:
            # Without RDKit, return raw generated strings
            tokens = self.model.sample(num_attempts, temperature, max_len)
            return self.tokenizer.decode_batch(tokens)

        self.model.eval()
        valid_smiles = []
        batch_size = min(32, num_attempts)
        num_batches = (num_attempts + batch_size - 1) // batch_size

        for _ in range(num_batches):
            tokens = self.model.sample(batch_size, temperature, max_len)
            smiles_list = self.tokenizer.decode_batch(tokens)
            for s in smiles_list:
                mol = Chem.MolFromSmiles(s)
                if mol is not None:
                    canonical = Chem.MolToSmiles(mol)
                    if canonical not in valid_smiles:
                        valid_smiles.append(canonical)

        return valid_smiles
