"""brief2net — AI-augmented Network Builder prototype.

Pipeline:  artist brief  ->  draft (AI step)  ->  NetworkSpec  ->  validator
           ->  Houdini build script (native operators + artist controls)

The technical artist stays in charge: the output is an *editable* node network,
never a final image or scene.
"""

__version__ = "0.1.0"

from .spec import NetworkSpec, NodeSpec, Connection, Control  # noqa: F401
