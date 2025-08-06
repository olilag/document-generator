#import "@preview/cmarker:0.1.6"
#import "@preview/mitex:0.2.4": mitex

#let _c = counter("problem")
#let _path-prefix = "/input/"

#let problem(directory, round, is-test) = {
  let meta = yaml(_path-prefix + directory + "/meta.yaml")
  let name = meta.title

  _c.step()

  context if is-test(round) [
    == #_c.display() - #name
  ] else [
    == #round.#_c.display() - #name
  ]

  cmarker.render(
    read(_path-prefix + directory + "/problem.md"),
    math: mitex,
    h1-level: 3,
    scope: (image: (path, alt: none) => image(_path-prefix + directory + "/" + path, alt: alt)),
    html: (details: (attrs, body) => []),
  )

  if is-test(round) {
    pagebreak(weak: true)
  }
}
