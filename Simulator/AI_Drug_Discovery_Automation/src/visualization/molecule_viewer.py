"""
Molecule Viewer
================
RDKit 기반 분자 구조 시각화 (2D/3D).
py3Dmol을 사용한 3D 뷰어 지원.
"""

import io
import base64
from typing import Optional, List, Tuple, Dict, Any
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import Draw, AllChem, Descriptors, rdDepictor
from rdkit.Chem.Draw import rdMolDraw2D

from src.config import get_config


# ──────────────────────────────────────────────────────────
# Molecule Viewer
# ──────────────────────────────────────────────────────────


class MoleculeViewer:
    """
    Molecular structure visualization utilities.

    Supports:
        - 2D structure images (PNG, SVG)
        - 3D structure visualization (via py3Dmol)
        - Multiple molecules grid view
        - High-quality image rendering
        - Image saving to file
    """

    def __init__(self, image_size: Tuple[int, int] = (400, 300), dpi: int = 150):
        self.image_size = image_size
        self.dpi = dpi
        self._output_dir = Path(get_config().result_dir) / "images"
        self._output_dir.mkdir(parents=True, exist_ok=True)

    # ──────────────────────────────────────────────────────────
    # 2D Rendering
    # ──────────────────────────────────────────────────────────

    def render_2d(
        self,
        mol: Chem.Mol,
        size: Optional[Tuple[int, int]] = None,
        add_hs: bool = False,
        kekulize: bool = True,
        highlight_atoms: Optional[List[int]] = None,
        highlight_bonds: Optional[List[int]] = None,
        atom_labels: Optional[Dict[int, str]] = None,
    ) -> Draw.MolDraw2DCairo:
        """
        Render a 2D molecular structure.

        Args:
            mol: RDKit Mol object
            size: Image size (width, height)
            add_hs: Include hydrogen atoms
            kekulize: Kekulize aromatic bonds
            highlight_atoms: Atoms to highlight
            highlight_bonds: Bonds to highlight
            atom_labels: Custom atom labels {idx: label}

        Returns:
            RDKit MolDraw2DCairo object
        """
        size = size or self.image_size

        if add_hs:
            mol = Chem.AddHs(mol)
        else:
            mol = Chem.RemoveHs(mol)

        # Generate 2D coordinates
        rdDepictor.SetPreferCoordGen(True)
        try:
            rdDepictor.Compute2DCoords(mol)
        except Exception:
            AllChem.Compute2DCoords(mol)

        # Prepare drawer
        drawer = rdMolDraw2D.MolDraw2DCairo(size[0], size[1], self.dpi)
        opts = drawer.drawOptions()
        opts.addStereoAnnotation = True
        opts.includeAtomTags = True

        if atom_labels:
            for idx, label in atom_labels.items():
                opts.atomLabels[idx] = label

        # Draw
        if highlight_atoms or highlight_bonds:
            drawer.DrawMolecule(
                mol,
                highlightAtoms=highlight_atoms or [],
                highlightBonds=highlight_bonds or [],
            )
        else:
            drawer.DrawMolecule(mol)

        drawer.FinishDrawing()
        return drawer

    def get_png(self, mol: Chem.Mol, **kwargs) -> bytes:
        """Get molecule image as PNG bytes."""
        drawer = self.render_2d(mol, **kwargs)
        return drawer.GetDrawingText()

    def get_svg(self, mol: Chem.Mol, size: Optional[Tuple[int, int]] = None) -> str:
        """Get molecule image as SVG string."""
        width, height = size or self.image_size
        drawer = rdMolDraw2D.MolDraw2DSVG(width, height, self.dpi)
        opts = drawer.drawOptions()
        drawer.DrawMolecule(mol)
        drawer.FinishDrawing()
        return drawer.GetDrawingText()

    def get_base64(self, mol: Chem.Mol, **kwargs) -> str:
        """Get molecule image as base64-encoded PNG string."""
        png_data = self.get_png(mol, **kwargs)
        return base64.b64encode(png_data).decode("utf-8")

    def get_data_uri(self, mol: Chem.Mol, **kwargs) -> str:
        """Get molecule image as data URI for HTML embedding."""
        b64 = self.get_base64(mol, **kwargs)
        return f"data:image/png;base64,{b64}"

    # ──────────────────────────────────────────────────────────
    # Grid View (Multiple Molecules)
    # ──────────────────────────────────────────────────────────

    def render_grid(
        self,
        mols: List[Chem.Mol],
        legends: Optional[List[str]] = None,
        mols_per_row: int = 4,
        sub_img_size: Tuple[int, int] = (300, 200),
        use_svg: bool = False,
    ) -> Any:
        """
        Render multiple molecules in a grid layout.

        Args:
            mols: List of RDKit Mol objects
            legends: List of legend strings
            mols_per_row: Number of molecules per row
            sub_img_size: Size of each sub-image
            use_svg: Use SVG format (default: PNG)

        Returns:
            Grid image as PNG bytes or SVG string
        """
        valid_mols = [(i, m) for i, m in enumerate(mols) if m is not None]
        if not valid_mols:
            return b"" if not use_svg else ""

        valid_indices = [v[0] for v in valid_mols]
        valid_mol_list = [v[1] for v in valid_mols]
        valid_legends = [legends[i] if legends and i < len(legends) else "" for i in valid_indices]

        try:
            img = Draw.MolsToGridImage(
                valid_mol_list,
                molsPerRow=mols_per_row,
                subImgSize=sub_img_size,
                legends=valid_legends,
                returnPNG=not use_svg,
            )
            return img
        except Exception:
            return b"" if not use_svg else ""

    def save_image(self, mol: Chem.Mol, filename: str, **kwargs) -> str:
        """
        Save molecule image to file.

        Args:
            mol: RDKit Mol object
            filename: Output filename

        Returns:
            Path to saved image file
        """
        filepath = self._output_dir / filename
        drawer = self.render_2d(mol, **kwargs)
        drawer.WriteDrawingText(str(filepath))
        return str(filepath)

    def save_grid_image(
        self,
        mols: List[Chem.Mol],
        filename: str,
        legends: Optional[List[str]] = None,
        **kwargs,
    ) -> str:
        """Save grid image to file."""
        filepath = self._output_dir / filename
        img = self.render_grid(mols, legends, **kwargs)
        with open(filepath, "wb") as f:
            f.write(img if isinstance(img, bytes) else img.encode())
        return str(filepath)

    # ──────────────────────────────────────────────────────────
    # 3D Viewer (py3Dmol)
    # ──────────────────────────────────────────────────────────

    def render_3d_html(self, mol: Chem.Mol, style: str = "stick") -> str:
        """
        Generate HTML with embedded 3D molecular viewer (py3Dmol).

        Args:
            mol: RDKit Mol object
            style: Display style ("stick", "line", "sphere", "cartoon")

        Returns:
            HTML string with embedded 3D viewer
        """
        try:
            import py3Dmol
        except ImportError:
            return "<p>py3Dmol not installed. Install with: pip install py3Dmol</p>"

        # Generate 3D coordinates
        mol_3d = Chem.AddHs(mol)
        try:
            params = AllChem.ETKDGv3()
            params.randomSeed = 42
            AllChem.EmbedMolecule(mol_3d, params)
            AllChem.MMFFOptimizeMolecule(mol_3d)
        except Exception:
            AllChem.Compute2DCoords(mol)

        # Convert to PDB block
        pdb_block = Chem.MolToPDBBlock(mol_3d)

        # Create py3Dmol view
        view = py3Dmol.view(width=500, height=400)
        view.addModel(pdb_block, "pdb")

        if style == "stick":
            view.setStyle({"stick": {"radius": 0.2}})
        elif style == "line":
            view.setStyle({"line": {}})
        elif style == "sphere":
            view.setStyle({"sphere": {"scale": 0.3}})
        elif style == "cartoon":
            view.setStyle({"cartoon": {"color": "spectrum"}})

        view.zoomTo()
        return view._make_html()

    def render_3d_from_pdb(self, pdb_path: str, style: str = "cartoon") -> str:
        """
        Generate HTML with 3D view from a PDB file.

        Args:
            pdb_path: Path to PDB file
            style: Display style

        Returns:
            HTML string
        """
        try:
            import py3Dmol
        except ImportError:
            return "<p>py3Dmol not installed</p>"

        with open(pdb_path) as f:
            pdb_data = f.read()

        view = py3Dmol.view(width=800, height=600)
        view.addModel(pdb_data, "pdb")

        if style == "cartoon":
            view.setStyle({"cartoon": {"color": "spectrum"}})
        elif style == "stick":
            view.setStyle({"stick": {"radius": 0.15}})

        view.zoomTo()
        return view._make_html()

    # ──────────────────────────────────────────────────────────
    # Highlights
    # ──────────────────────────────────────────────────────────

    def highlight_substructure(
        self,
        mol: Chem.Mol,
        substructure_smarts: str,
        color: str = "red",
    ) -> bytes:
        """Highlight a substructure match in the molecule."""
        pattern = Chem.MolFromSmarts(substructure_smarts)
        if pattern is None:
            return self.get_png(mol)

        matches = mol.GetSubstructMatches(pattern)
        if not matches:
            return self.get_png(mol)

        # Flatten matched atom indices
        highlight_atoms = [atom for match in matches for atom in match]
        return self.get_png(mol, highlight_atoms=highlight_atoms)

    def highlight_property(
        self,
        mol: Chem.Mol,
        property_name: str,
        colormap: str = "RdYlGn",
    ) -> bytes:
        """
        Color atoms by a property value.

        Args:
            mol: RDKit Mol object
            property_name: Atomic property to visualize
            colormap: Matplotlib colormap name

        Returns:
            PNG image bytes
        """
        # Get atomic property values
        from rdkit.Chem import Descriptors

        num_atoms = mol.GetNumAtoms()

        if property_name == "gasteiger":
            AllChem.ComputeGasteigerCharges(mol)
            values = [float(mol.GetAtomWithIdx(i).GetDoubleProp("_GasteigerCharge"))
                      for i in range(num_atoms)]
        elif property_name == "partial_charge":
            AllChem.ComputeGasteigerCharges(mol)
            values = [float(mol.GetAtomWithIdx(i).GetDoubleProp("_GasteigerCharge"))
                      for i in range(num_atoms)]
        else:
            values = [0.0] * num_atoms

        # Normalize to 0-1 for coloring
        min_v, max_v = min(values), max(values)
        if max_v > min_v:
            norm_values = [(v - min_v) / (max_v - min_v) for v in values]
        else:
            norm_values = [0.5] * len(values)

        # Use atom color highlighting
        try:
            import matplotlib.colors as mcolors
            cmap = mcolors.LinearSegmentedColormap.from_list("custom", ["blue", "white", "red"])
            atom_colors = {}
            for i, nv in enumerate(norm_values):
                r, g, b, _ = cmap(nv)
                atom_colors[i] = (r, g, b)

            drawer = rdMolDraw2D.MolDraw2DCairo(self.image_size[0], self.image_size[1], self.dpi)
            opts = drawer.drawOptions()
            drawer.DrawMolecule(mol, highlightAtoms=list(range(num_atoms)),
                                highlightAtomColors=atom_colors)
            drawer.FinishDrawing()
            return drawer.GetDrawingText()
        except ImportError:
            return self.get_png(mol)


# ──────────────────────────────────────────────────────────
# Convenience Functions
# ──────────────────────────────────────────────────────────


def view_molecule(
    smiles: str,
    view_type: str = "2d",
    size: Tuple[int, int] = (400, 300),
    **kwargs,
) -> Any:
    """
    Quick molecule visualization from SMILES.

    Args:
        smiles: SMILES string
        view_type: "2d", "3d", "base64", "svg"
        size: Image size

    Returns:
        Image data based on view_type
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles}")

    viewer = MoleculeViewer(image_size=size)

    if view_type == "2d":
        return viewer.get_png(mol, **kwargs)
    elif view_type == "3d":
        return viewer.render_3d_html(mol, **kwargs)
    elif view_type == "base64":
        return viewer.get_base64(mol, **kwargs)
    elif view_type == "svg":
        return viewer.get_svg(mol, **kwargs)
    elif view_type == "data_uri":
        return viewer.get_data_uri(mol, **kwargs)
    else:
        raise ValueError(f"Unknown view_type: {view_type}")


def save_molecule_image(
    smiles: str,
    filename: str,
    size: Tuple[int, int] = (400, 300),
    **kwargs,
) -> str:
    """Save a molecule image from SMILES."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles}")

    viewer = MoleculeViewer(image_size=size)
    return viewer.save_image(mol, filename, **kwargs)
