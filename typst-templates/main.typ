#import "document.typ": document

#let d = sys.inputs.root
#let meta = yaml("/" + d + "/meta.yaml")

#document(meta.volume, meta.year, meta.round, meta.sources)
