"""
Compound Library Manager
========================

화합물 라이브러리 로딩, 필터링, 내보내기를 위한 모듈.

Supports:
    - SDF/SMILES 파일에서 라이브러리 로딩
    - PubChem API를 통한 화합물 검색
    - 속성 기반 필터링
    - 다양한 형식으로 내보내기
"""

import json
import csv
import logging
import random
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable, Iterator
from dataclasses import dataclass, field, asdict

import numpy as np

logger = logging.getLogger(__name__)

try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, AllChem
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False

from src.molecular.rdkit_utils import MolFromSMILES, MolFromSDF, MolToSMILES
from src.molecular.descriptors import (
    lipinski_rule_of_five,
    veber_rule,
)


# ──────────────────────────────────────────────────────────
# Data Models
# ──────────────────────────────────────────────────────────


@dataclass
class Compound:
    """A chemical compound with metadata."""
    id: str
    smiles: str
    name: str = ""
    mol: Optional[Any] = None  # RDKit Mol object (lazy loaded)
    properties: Dict[str, float] = field(default_factory=dict)
    source: str = ""
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.mol is None and RDKIT_AVAILABLE and self.smiles:
            try:
                self.mol = Chem.MolFromSmiles(self.smiles)
            except Exception:
                pass

    def to_smiles(self) -> str:
        return self.smiles

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "smiles": self.smiles,
            "name": self.name,
            "properties": self.properties,
            "source": self.source,
            "tags": self.tags,
        }


# ──────────────────────────────────────────────────────────
# Compound Library Manager
# ──────────────────────────────────────────────────────────


class CompoundLibraryManager:
    """
    Manage compound libraries for virtual screening.

    Supports loading compounds from various formats (SDF, SMILES, CSV),
    filtering by properties, and exporting results.

    Usage:
        manager = CompoundLibraryManager()
        count = manager.load_from_smiles_file("compounds.smi")
        filtered = manager.filter_by_lipinski()
        manager.export_library("filtered.sdf")
    """

    def __init__(self, library_path: Optional[str] = None, format: str = "sdf"):
        self.compounds: List[Compound] = []
        self.library_path = str(library_path) if library_path else ""
        self.format = format

        if library_path:
            self.load_library()

    def load_library(self) -> int:
        """Load library from the configured path."""
        if not self.library_path:
            logger.warning("No library path configured.")
            return 0

        ext = Path(self.library_path).suffix.lower()
        if ext in (".sdf", ".mol"):
            return self.load_from_sdf(self.library_path)
        elif ext in (".smi", ".smiles", ".txt"):
            return self.load_from_smiles_file(self.library_path)
        elif ext == ".csv":
            return self.load_from_csv(self.library_path)
        else:
            logger.error(f"Unsupported format: {ext}")
            return 0

    def load_from_smiles_file(self, path: str, delimiter: str = " ") -> int:
        """
        Load compounds from a SMILES file.

        Format: "SMILES [delimiter] name" per line.

        Args:
            path: Path to SMILES file.
            delimiter: Delimiter between SMILES and name.

        Returns:
            Number of compounds loaded.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        count = 0
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(delimiter, 1)
                smiles = parts[0].strip()
                name = parts[1].strip() if len(parts) > 1 else ""
                if smiles:
                    cpd_id = f"CMP{count + 1:06d}"
                    self.compounds.append(Compound(
                        id=cpd_id, smiles=smiles, name=name,
                        source=str(path)
                    ))
                    count += 1

        logger.info(f"Loaded {count} compounds from {path}")
        return count

    def load_from_sdf(self, path: str) -> int:
        """
        Load compounds from an SDF file.

        Args:
            path: Path to SDF file.

        Returns:
            Number of compounds loaded.
        """
        molecules = MolFromSDF(path)
        count = 0
        for i, mol in enumerate(molecules):
            if mol is None:
                continue
            smiles = MolToSMILES(mol)
            if not smiles:
                continue
            cpd_id = f"CMP{count + 1:06d}"

            # Extract properties from SDF data fields
            props = {}
            try:
                for key in mol.GetPropsAsDict():
                    val = mol.GetPropsAsDict()[key]
                    if isinstance(val, (int, float)):
                        props[key] = float(val)
            except Exception:
                pass

            self.compounds.append(Compound(
                id=cpd_id, smiles=smiles,
                name=mol.GetProp("_Name") if mol.HasProp("_Name") else "",
                mol=mol, properties=props,
                source=str(path),
            ))
            count += 1

        logger.info(f"Loaded {count} compounds from SDF: {path}")
        return count

    def load_from_csv(self, path: str, smiles_col: str = "smiles") -> int:
        """
        Load compounds from a CSV file.

        Args:
            path: Path to CSV file.
            smiles_col: Column name containing SMILES.

        Returns:
            Number of compounds loaded.
        """
        path = Path(path)
        count = 0
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            if smiles_col not in reader.fieldnames:
                logger.error(f"CSV missing SMILES column: {smiles_col}")
                return 0
            for row in reader:
                smiles = row[smiles_col].strip()
                if not smiles:
                    continue
                props = {}
                for key, val in row.items():
                    if key != smiles_col and val:
                        try:
                            props[key] = float(val)
                        except ValueError:
                            pass
                cpd_id = f"CMP{count + 1:06d}"
                self.compounds.append(Compound(
                    id=cpd_id, smiles=smiles,
                    name=row.get("name", row.get("ID", "")),
                    properties=props, source=str(path),
                ))
                count += 1

        logger.info(f"Loaded {count} compounds from CSV: {path}")
        return count

    def load_from_pubchem(self, query: str, max_compounds: int = 100) -> int:
        """
        Fetch compounds from PubChem by keyword search.

        Args:
            query: Search query (e.g., "aspirin", "kinase inhibitor").
            max_compounds: Maximum compounds to fetch.

        Returns:
            Number of compounds loaded.
        """
        try:
            import requests
        except ImportError:
            logger.error("requests is required for PubChem API.")
            return 0

        try:
            # Search PubChem
            search_url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{}/cids/JSON"
            response = requests.get(search_url.format(query), timeout=30)
            if response.status_code != 200:
                logger.warning(f"PubChem search failed: {response.status_code}")
                return 0

            data = response.json()
            cids = data.get("IdentifierList", {}).get("CID", [])[:max_compounds]
            if not cids:
                logger.warning(f"No compounds found for: {query}")
                return 0

            # Fetch SMILES
            smiles_url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{}/property/CanonicalSMILES,MolecularFormula,MW/JSON"
            response = requests.get(smiles_url.format(",".join(map(str, cids))), timeout=30)
            if response.status_code != 200:
                return 0

            props_data = response.json()
            for prop in props_data.get("PropertyTable", {}).get("Properties", []):
                smiles = prop.get("CanonicalSMILES", "")
                if smiles:
                    cpd_props = {}
                    if "MW" in prop:
                        cpd_props["MW"] = prop["MW"]
                    self.compounds.append(Compound(
                        id=f"PUBCHEM_{prop['CID']}",
                        smiles=smiles,
                        name=query,
                        properties=cpd_props,
                        source="PubChem",
                    ))

            count = len(self.compounds) - (len(self.compounds) - min(len(cids), max_compounds))
            logger.info(f"Fetched {count} compounds from PubChem for: {query}")
            return count

        except Exception as e:
            logger.error(f"PubChem API error: {e}")
            return 0

    # ──────────────────────────────────────────────
    # Access Methods
    # ──────────────────────────────────────────────

    def get_compound(self, cpd_id: str) -> Optional[Compound]:
        """Get a compound by ID."""
        for cpd in self.compounds:
            if cpd.id == cpd_id:
                return cpd
        return None

    def get_compounds(self, ids: List[str]) -> List[Compound]:
        """Get multiple compounds by IDs."""
        return [c for c in self.compounds if c.id in ids]

    def random_sample(self, n: int) -> List[Compound]:
        """Get a random sample of compounds."""
        return random.sample(self.compounds, min(n, len(self.compounds)))

    def __iter__(self) -> Iterator[Compound]:
        return iter(self.compounds)

    def __len__(self) -> int:
        return len(self.compounds)

    # ──────────────────────────────────────────────
    # Filtering
    # ──────────────────────────────────────────────

    def filter_by_property(self, prop: str, min_val: float, max_val: float) -> List[Compound]:
        """Filter compounds by a numeric property range."""
        results = []
        for cpd in self.compounds:
            if not cpd.mol and RDKIT_AVAILABLE:
                cpd.mol = Chem.MolFromSmiles(cpd.smiles)
            if cpd.mol:
                try:
                    val = self._get_property(cpd.mol, prop)
                    if min_val <= val <= max_val:
                        results.append(cpd)
                except (ValueError, TypeError):
                    continue
        logger.info(f"Filter by {prop} [{min_val}, {max_val}]: {len(results)}/{len(self.compounds)}")
        return results

    def filter_by_lipinski(self) -> List[Compound]:
        """Filter compounds that pass Lipinski Rule of Five."""
        results = []
        for cpd in self.compounds:
            if not cpd.mol and RDKIT_AVAILABLE:
                cpd.mol = Chem.MolFromSmiles(cpd.smiles)
            if cpd.mol and lipinski_rule_of_five(cpd.mol).passed:
                results.append(cpd)
        logger.info(f"Lipinski filter: {len(results)}/{len(self.compounds)} passed")
        return results

    def filter_by_veber(self) -> List[Compound]:
        """Filter compounds that pass Veber rule."""
        results = []
        for cpd in self.compounds:
            if not cpd.mol and RDKIT_AVAILABLE:
                cpd.mol = Chem.MolFromSmiles(cpd.smiles)
            if cpd.mol and veber_rule(cpd.mol).passed:
                results.append(cpd)
        logger.info(f"Veber filter: {len(results)}/{len(self.compounds)} passed")
        return results

    def filter_by_custom(self, func: Callable[[Compound], bool]) -> List[Compound]:
        """Filter compounds using a custom function."""
        return [c for c in self.compounds if func(c)]

    def _get_property(self, mol: Any, prop: str) -> float:
        """Get a molecular property by name."""
        prop_map = {
            "MW": Descriptors.MolWt,
            "LogP": Descriptors.MolLogP,
            "HBD": Descriptors.NumHDonors,
            "HBA": Descriptors.NumHAcceptors,
            "TPSA": Descriptors.TPSA,
            "RotB": Descriptors.NumRotatableBonds,
            "HeavyAtoms": Descriptors.HeavyAtomCount,
            "RingCount": lambda m: Descriptors.RingCount(m) if hasattr(Descriptors, 'RingCount') else 0,
        }
        func = prop_map.get(prop)
        if func:
            return float(func(mol))
        raise ValueError(f"Unknown property: {prop}")

    # ──────────────────────────────────────────────
    # Statistics & Export
    # ──────────────────────────────────────────────

    def statistics(self) -> Dict[str, Any]:
        """Compute library statistics."""
        if not self.compounds:
            return {"count": 0}
        stats = {
            "count": len(self.compounds),
            "sources": {},
            "unique_smiles": len(set(c.smiles for c in self.compounds)),
        }
        for cpd in self.compounds:
            stats["sources"][cpd.source] = stats["sources"].get(cpd.source, 0) + 1
        return stats

    def export_library(self, format: str = "sdf", path: Optional[str] = None) -> int:
        """
        Export the compound library to a file.

        Args:
            format: Output format ('sdf', 'smi', 'csv', 'json').
            path: Output path (auto-generated if None).

        Returns:
            Number of compounds exported.
        """
        if not self.compounds:
            return 0

        if path is None:
            path = str(Path(self.library_path).parent / f"export.{format}")

        count = 0
        if format == "sdf":
            writer = Chem.SDWriter(str(path))
            for cpd in self.compounds:
                if cpd.mol:
                    for key, val in cpd.properties.items():
                        cpd.mol.SetProp(key, str(val))
                    writer.write(cpd.mol)
                    count += 1
            writer.close()

        elif format == "smi":
            with open(path, "w") as f:
                for cpd in self.compounds:
                    f.write(f"{cpd.smiles} {cpd.name or cpd.id}\n")
                    count += 1

        elif format == "csv":
            with open(path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["id", "smiles", "name"] + list(self.compounds[0].properties.keys()))
                for cpd in self.compounds:
                    row = [cpd.id, cpd.smiles, cpd.name]
                    row.extend(str(cpd.properties.get(k, "")) for k in self.compounds[0].properties.keys())
                    writer.writerow(row)
                    count += 1

        elif format == "json":
            data = [c.to_dict() for c in self.compounds]
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
            count = len(self.compounds)

        logger.info(f"Exported {count} compounds to {path}")
        return count

    def add_compound(self, compound: Compound) -> None:
        """Add a compound to the library."""
        self.compounds.append(compound)

    def remove_compound(self, cpd_id: str) -> bool:
        """Remove a compound by ID."""
        for i, cpd in enumerate(self.compounds):
            if cpd.id == cpd_id:
                self.compounds.pop(i)
                return True
        return False

    def __repr__(self) -> str:
        return f"CompoundLibraryManager(compounds={len(self.compounds)})"
