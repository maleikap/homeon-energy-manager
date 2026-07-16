# HomeOn Energy Manager

Integracja Home Assistant dla HomeOn EMS.

## Wersja 0.2.36

### Home Battery Priority

- Dodano przełącznik `HomeOn Tryb handlu baterią`.
- Domyślnie handel baterią jest wyłączony.
- Gdy bateria zasila gospodarstwo domowe, HomeOn nie zmienia nastaw Deye ani trybu pracy falownika.
- Gdy handel baterią jest wyłączony, HomeOn nie ustawia sprzedaży energii z magazynu.
- Dodano diagnostykę ochrony domu:
  - tryb handlu baterią,
  - ochrona domu bateria zasila dom,
  - moc baterii dla domu,
  - powód ochrony domu.

## Instalacja przez HACS

Repozytorium niestandardowe:

`maleikap/homeon-energy-manager`

Typ: Integration
