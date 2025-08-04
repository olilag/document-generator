#import "problem.typ": problem

#let _round-is-test(round) = {
  round == none
}

#let _header-string(round) = {
  if _round-is-test(round) [
    Testovanie
  ] else [
    Zadania #round. kola
  ]
}

#let _title-string(round) = {
  if _round-is-test(round) [
    Testovanie šifier pre súťaž Štyri
  ] else [
    Zadania #round. kola
  ]
}

#let document(volume, year, round, sources) = {
  set text(lang: "sk", size: 12pt)

  set page(
    paper: "a4",
    margin: (top: 5.5cm, left: 1.5cm, right: 1.5cm),
    header: context {
      if counter(page).get().first() == 1 [
        #box(image("/brand/trojsten/logo/blue.svg", height: 2cm))
        #h(1fr)
        #box({
          set align(horizon + center)
          stack(
            dir: ttb,
            spacing: 10%,
            text("Štyri", size: 16pt),
            text([#numbering("I", volume). ročník, #year], size: 16pt),
            text("Štyri, Trojsten FMFI UK, Mlynská dolina, 842 48 Bratislava", size: 11pt),
          )
        })
        #h(1fr)
        #box(image("/brand/susi/logo/color.svg", height: 2cm))
      ] else [
        _#_header-string(round)_
        #h(1fr)
        #box(image("/brand/susi/logo/color.svg", height: 5mm))
      ]
      line(length: 100%)
    },
    footer: context [
      #show link: set text(fill: blue, size: 11pt)
      #line(length: 100%)
      #link("mailto:susi@trojsten.sk")
      #h(1fr)
      #counter(page).display("1")
      #h(1fr)
      #link("https://susi.trojsten.sk")
    ],
  )

  align(center)[= #_title-string(round)]

  pagebreak()
  set page(margin: (top: 3cm))

  let pb = _round-is-test(round)

  for dir in sources {
    problem(dir, round, _round-is-test)
  }
}
