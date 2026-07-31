# HomeOn Energy Manager

HomeOn Energy Manager to integracja Home Assistant zarządzająca instalacją fotowoltaiczną, magazynem energii i falownikiem na podstawie bieżącego zużycia, prognozy produkcji oraz dynamicznych cen energii.

Manager wyznacza cele ładowania i rozładowania, planuje zakup oraz sprzedaż energii i może przekazywać bezpieczne polecenia do falownika. Dom i bezpieczeństwo magazynu zawsze mają pierwszeństwo przed handlem energią.

## Najważniejsze funkcje

- bieżący bilans PV, domu, sieci i magazynu,
- planowanie ładowania oraz sprzedaży według cen energii,
- prognozowanie potrzeb energetycznych domu,
- wykorzystanie prognozy produkcji PV,
- ocena realnej jakości produkcji PV,
- przygotowanie miejsca w magazynie przed tanią lub ujemną ceną,
- ochrona minimalnego i awaryjnego SOC,
- tryb testowy `dry-run`,
- kontrolowane sterowanie falownikiem Deye,
- uczenie typowego zużycia domu,
- diagnostyka jakości danych i tryb `SAFE MODE`.

## Wymagania

- Home Assistant 2025.1 lub nowszy,
- HACS,
- instalacja fotowoltaiczna z magazynem energii,
- integracja udostępniająca encje falownika i baterii,
- integracja dynamicznych cen zakupu oraz sprzedaży energii.

## Integracje potrzebne do pełnej funkcjonalności

### Falownik i magazyn energii

Wymagana jest integracja Deye/Solarman lub inna zgodna integracja udostępniająca:

- SOC magazynu,
- moc baterii,
- moc PV,
- moc domu,
- moc sieci,
- przełącznik ładowania baterii z sieci,
- przełącznik eksportu energii,
- encję ustawiania mocy eksportu,
- encje maksymalnego prądu ładowania i rozładowania.

Nazwy encji mogą być inne — wybiera się je podczas konfiguracji HomeOn Energy Manager.

### Dynamiczne ceny energii

Potrzebne są osobne sensory:

- aktualnej ceny zakupu energii,
- aktualnej ceny sprzedaży energii.

Manager współpracuje między innymi z danymi udostępnianymi przez Pstryk, jeżeli odpowiednie sensory cen są dostępne w Home Assistant.

### Prognoza produkcji PV

Zalecana jest jedna z integracji:

- Forecast.Solar,
- Solcast PV Forecast.

Manager wykorzystuje prognozę produkcji na dziś i jutro. Bez prognozy część funkcji planowania będzie ograniczona.

## Instalacja przez HACS

1. Otwórz HACS w Home Assistant.
2. Przejdź do sekcji **Integracje**.
3. Dodaj repozytorium niestandardowe:

   `https://github.com/maleikap/homeon-energy-manager`

4. Wybierz kategorię **Integracja**.
5. Pobierz najnowsze wydanie HomeOn Energy Manager.
6. Uruchom ponownie Home Assistant.
7. Przejdź do **Ustawienia → Urządzenia i usługi → Dodaj integrację**.
8. Wyszukaj **HomeOn Energy Manager**.

Nie trzeba ręcznie kopiować plików do katalogu `custom_components`.

## Pierwsza konfiguracja

Podczas dodawania integracji należy wybrać:

- sensory SOC, mocy baterii, PV, domu i sieci,
- sensory ceny zakupu i sprzedaży,
- opcjonalne sensory prognozy PV,
- pojemność magazynu energii,
- minimalny i awaryjny SOC,
- kierunki znaków mocy baterii i sieci,
- encje sterujące falownikiem.

Po instalacji sterowanie falownikiem jest wyłączone, a `dry-run` pozostaje włączony. Pozwala to sprawdzić decyzje managera przed wysłaniem rzeczywistych poleceń.

## Pojemność magazynu

W urządzeniu **HomeOn Energy Manager** dostępna jest encja:

`number.homeon_pojemnosc_magazynu`

Wartość należy ustawić jako rzeczywistą użyteczną pojemność całego magazynu w kWh. Ustawienie jest zapisywane i od razu wykorzystywane przez planowanie, cele SOC oraz obliczenia energii.

Przykład dla magazynu 15 kWh:

- SOC 27% = około 4,05 kWh energii w magazynie,
- wolne miejsce = około 10,95 kWh.

Manager udostępnia osobne sensory:

- **Energia w magazynie** — aktualna ilość energii wynikająca z SOC,
- **Wolne miejsce w magazynie** — ilość energii możliwa do doładowania,
- **Energia dostępna do sprzedaży** — nadwyżka ponad wyznaczony bezpieczny cel.

## Bezpieczne uruchomienie

1. Ustaw właściwą pojemność magazynu.
2. Sprawdź kierunki mocy baterii i sieci.
3. Pozostaw `dry-run` włączony.
4. Obserwuj tryb EMS, decyzję i plan zmian Deye.
5. Dopiero po sprawdzeniu danych włącz sterowanie falownikiem.

Jeżeli wymagane dane są nieaktualne lub niepoprawne, manager przechodzi do `SAFE MODE` i ogranicza wykonywanie poleceń.

## HomeOn Energy Card

Do czytelnej prezentacji pracy managera można użyć:

[HomeOn Energy Card](https://github.com/maleikap/homeon-energy-card)

Karta pokazuje przepływ energii, magazyn, ceny, prognozę PV, decyzje managera oraz dzienny bilans finansowy.

## Wsparcie projektu

Jeżeli projekt jest przydatny, możesz wesprzeć jego dalszy rozwój:

[Postaw kawę przez BuyCoffee](https://buycoffee.to/homeon)
