"""py2app entry point — kept tiny so py2app's modulegraph behaves."""
from asutools.__main__ import main
import sys

if __name__ == "__main__":
    sys.exit(main())
