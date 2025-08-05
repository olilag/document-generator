#import "@preview/cmarker:0.1.6"
#import "@preview/mitex:0.2.4": mitex

#let _c = counter("problem")

#let problem(directory, round, is-test) = {
  let meta = yaml("/" + directory + "/meta.yaml")
  let name = meta.title

  _c.step()

  context if is-test(round) [
    == #_c.display() - #name
  ] else [
    == #round.#_c.display() - #name
  ]
  cmarker.render(
    read("/" + directory + "/problem.md"),
    math: mitex,
    h1-level: 3,
    scope: (image: (path, alt: none) => image("/" + directory + "/" + path, alt: alt)),
    html: (details: (attrs, body) => []),
  )
  if is-test(round) {
    pagebreak(weak: true)
  }
}
