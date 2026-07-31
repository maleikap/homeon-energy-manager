<p align="center">
  <img src="brand/logo.svg" alt="HomeOn" width="520">
</p>

<h1 align="center">HomeOn Energy Manager</h1>

<p align="center">
  Inteligentny manager energii dla Home Assistant, instalacji fotowoltaicznej, magazynu energii i taryf dynamicznych.
</p>

<p align="center">
  <a href="https://github.com/maleikap/homeon-energy-manager/releases"><img src="https://img.shields.io/github/v/release/maleikap/homeon-energy-manager" alt="Latest release"></a>
  <a href="https://github.com/maleikap/homeon-energy-manager"><img src="https://img.shields.io/badge/Home%20Assistant-HACS-41BDF5" alt="Home Assistant HACS"></a>
  <a href="https://buycoffee.to/homeon"><img src="https://img.shields.io/badge/Support%20HomeOn-BuyCoffee-F6C344" alt="Support HomeOn on BuyCoffee"></a>
</p>

## Przeznaczenie

HomeOn Energy Manager analizuje produkcję PV, zużycie domu, stan magazynu, prognozę pogody oraz dynamiczne ceny energii. Na tej podstawie planuje ładowanie, wykorzystanie i sprzedaż energii oraz może bezpiecznie sterować falownikiem.

Najważniejsze funkcje:

- bieżący bilans PV, domu, sieci i magazynu,
- planowanie ładowania i sprzedaży według cen energii,
- wyznaczanie celów SOC magazynu,
- prognozowanie potrzeb energetycznych domu,
- wykorzystanie prognozy produkcji PV,
- ocena jakości rzeczywistej produkcji PV,
- przygotowanie miejsca przed tanią lub ujemną ceną,
- ochrona minimalnego i awaryjnego SOC,
- uczenie typowego zużycia domu,
- diagnostyka danych i tryb `SAFE MODE`,
- bezpieczne sterowanie falownikiem Deye,
- tryb testowy `dry-run`.

Dom i bezpieczeństwo magazynu zawsze mają pierwszeństwo przed handlem energią.

## Wymagane elementy

| Element | Zastosowanie |
| --- | --- |
| Home Assistant 2025.1 lub nowszy | Środowisko uruchomieniowe |
| HACS | Automatyczna instalacja i aktualizacja integracji |
| Instalacja PV z magazynem energii | Źródło produkcji, SOC i mocy baterii |
| Integracja falownika Deye/Solarman lub zgodna | Odczyty instalacji oraz sterowanie falownikiem |
| Integracja taryfy dynamicznej | Aktualne ceny zakupu i sprzedaży energii |

## Integracje zalecane do pełnej funkcjonalności

### Pstryk AIO

Pstryk AIO może dostarczać aktualne ceny zakupu i sprzedaży energii wykorzystywane przez managera. W konfiguracji należy wskazać osobne sensory:

- aktualnej ceny zakupu energii,
- aktualnej ceny sprzedaży energii.

Manager nie korzysta z dziennego kosztu ani dziennej wartości sprzedaży jako aktualnej ceny. Te encje są przeznaczone do prezentacji bilansu finansowego w HomeOn Energy Card.

### Prognoza produkcji PV

Do dokładnego planowania magazynu zalecana jest jedna z integracji:

- Forecast.Solar,
- Solcast PV Forecast,
- inne źródło udostępniające prognozę produkcji dzisiaj i jutro.

Brak prognozy nie blokuje uruchomienia integracji, ale ogranicza jakość planowania.

### Integracja falownika

HomeOn Energy Manager potrzebuje co najmniej:

- SOC magazynu,
- mocy baterii,
- mocy PV,
- mocy domu,
- mocy sieci,
- przełącznika ładowania z sieci,
- przełącznika eksportu nadwyżki,
- nastawy mocy eksportu,
- nastawy maksymalnego prądu ładowania,
- nastawy maksymalnego prądu rozładowania.

Do pełnego sterowania Deye potrzebna jest również encja trybu pracy falownika udostępniająca właściwe opcje `Export First` i `Zero Export To CT`.

Nazwy encji zależą od użytej integracji falownika i konfiguracji Home Assistant.

## Instalacja przez HACS

1. W HACS otwórz menu repozytoriów niestandardowych.
2. Dodaj repozytorium jako typ **Integracja**:

```text
https://github.com/maleikap/homeon-energy-manager
```

3. Pobierz HomeOn Energy Manager.
4. Uruchom ponownie Home Assistant.
5. Przejdź do **Ustawienia → Urządzenia i usługi → Dodaj integrację**.
6. Wyszukaj **HomeOn Energy Manager**.

HACS instaluje integrację automatycznie. Nie należy ręcznie kopiować plików do `/config/custom_components`.

## Konfiguracja

Podczas dodawania integracji należy wskazać:

- sensory SOC, mocy baterii, PV, domu i sieci,
- sensory aktualnej ceny zakupu i sprzedaży,
- opcjonalne sensory prognozy PV,
- pojemność magazynu energii,
- minimalny i awaryjny SOC,
- kierunki znaków mocy baterii i sieci,
- encje sterujące falownikiem.

Po instalacji sterowanie falownikiem jest wyłączone, a `dry-run` włączony. Pozwala to sprawdzić decyzje managera przed wysłaniem rzeczywistych poleceń.

### Pojemność magazynu

W urządzeniu **HomeOn Energy Manager** dostępna jest encja:

```text
number.homeon_pojemnosc_magazynu
```

Należy w niej ustawić rzeczywistą użyteczną pojemność całego magazynu w kWh. Wartość zapisuje się automatycznie i jest od razu używana do obliczania celów SOC, wolnego miejsca i energii dostępnej do sprzedaży.

Dla magazynu 15 kWh i SOC 27%:

- energia w magazynie wynosi około 4,05 kWh,
- wolne miejsce wynosi około 10,95 kWh.

Są to dwie różne wartości.

### Progi ekonomiczne

Najważniejsze ustawienia dostępne jako encje `number`:

- **Cena dobrej sprzedaży** — minimalna cena pozwalająca rozpocząć sprzedaż,
- **Cena taniego ładowania** — maksymalna cena zwykłego ładowania z sieci,
- **Minimalny zysk arbitrażu** — minimalny przewidywany zysk ze sprzedaży,
- **Koszt cyklu baterii** — koszt uwzględniany przy ocenie opłacalności.

Dobra cena sprzedaży ma pierwszeństwo przed zwykłym tanim ładowaniem. Ładowanie przy cenie ujemnej, `SAFE MODE` i awaryjny SOC pozostają nadrzędnymi zabezpieczeniami.

### Ładowanie w najgorszych godzinach sprzedaży

Przy dużej prognozie produkcji PV manager nie zapełnia magazynu od rana. Analizuje dzisiejszy harmonogram ceny sprzedaży i wybiera 2–3 najgorsze pozostałe godziny.

Przykład:

- prognoza PV: 50 kWh,
- pojemność magazynu: 15 kWh,
- rano magazyn ma jeszcze wolne miejsce.

HomeOn działa wtedy następująco:

1. Poza najgorszymi godzinami ustawia `Export First` i sprzedaje bieżącą nadwyżkę PV.
2. Nie wymusza rozładowania magazynu tylko po to, aby eksportować PV.
3. W 2–3 godzinach z najniższą ceną sprzedaży ustawia `Zero Export To CT`.
4. Wyłącza ładowanie z sieci i kieruje nadwyżkę PV do magazynu.
5. Po zakończeniu taniego okna ponownie pozwala sprzedawać produkcję.

Liczba godzin jest dobierana automatycznie:

- na podstawie wolnego miejsca do 95% SOC,
- na podstawie prognozowanej średniej mocy PV,
- minimum 2 i maksimum 3 godziny.

Strategia uruchamia się, gdy prognoza PV wynosi co najmniej 150% pojemności magazynu i nie mniej niż 20 kWh. Wymaga włączonego trybu handlu baterią oraz harmonogramu ceny sprzedaży w atrybutach sensora taryfy.

Cena używana do decyzji jest pobierana z przedziału harmonogramu odpowiadającego bieżącej godzinie. Wpis godzinowy, np. `15:00`, obowiązuje aż do `15:59`. Stan encji jest używany jako bezpieczny fallback tylko wtedy, gdy w harmonogramie brakuje bieżącego przedziału. Źródło można sprawdzić w encji `Źródło ceny sprzedaży`.

Po zakończeniu wybranych najgorszych godzin strategia zwalniania miejsca zostaje zamknięta. Jeżeli bieżący przedział jest najlepszym opłacalnym oknem sprzedaży, manager może rozpocząć sprzedaż magazynu również wtedy, gdy cena jest nieznacznie niższa od ręcznie ustawionego progu `Cena dobrej sprzedaży`.

Strategia działa kolejno: przed najgorszymi godzinami `PV_PRICE_EXPORT` sprzedaje bieżącą produkcję i zachowuje miejsce w magazynie; w wybranych najgorszych godzinach `PV_LOW_PRICE_CHARGE` ładuje baterię z PV; po ich zakończeniu `WAIT_BETTER_SELL_PRICE` zachowuje energię baterii i może sprzedawać bieżącą nadwyżkę PV; w najlepszym opłacalnym oknie `SELL_BATTERY_HIGH_PRICE` sprzedaje dostępną energię magazynu.

### Optymalizator 24 h

Optymalizator łączy godzinowy harmonogram cen z wyuczonym profilem zużycia domu i produkcji PV. Oblicza dynamiczny cel SOC, ilość energii możliwą do sprzedaży, wymagany czas rozładowania, przewidywany zysk oraz zalecany moment rozpoczęcia sprzedaży. Jeżeli pełna sprzedaż nie zmieściłaby się w najlepszej godzinie, manager może rozpocząć ją wcześniej w nadal opłacalnym oknie. Prognoza PV jest automatycznie korygowana na podstawie stosunku rzeczywistej produkcji do prognozy z poprzednich dni.

Nowe parametry pozwalają ustawić sprawność ładowania i rozładowania oraz napięcie nominalne baterii. Domyślne wartości to odpowiednio 94%, 94% i 51,2 V.

### Zdarzenia i powiadomienia

Przy zmianie trybu lub statusu wykonania komend manager emituje zdarzenie `homeon_energy_manager_decision`. Dane zdarzenia zawierają tryb, powód, SOC, cenę sprzedaży, następną akcję, jej godzinę oraz status potwierdzenia Deye. Zdarzenie można wykorzystać jako wyzwalacz automatyzacji Home Assistant wysyłającej powiadomienie mobilne albo wiadomość Telegram.

Wybrane godziny i aktualną decyzję pokazują sensory:

- **Strategia cenowa PV**,
- **Najgorsze godziny sprzedaży PV**,
- **Powód strategii cenowej PV**,
- **Liczba godzin ładowania PV**.

## Bezpieczne uruchomienie

1. Ustaw właściwą pojemność magazynu.
2. Sprawdź kierunki mocy baterii i sieci.
3. Pozostaw `dry-run` włączony.
4. Obserwuj tryb EMS, decyzję i plan zmian Deye.
5. Sprawdź działanie ładowania oraz wyłączenia eksportu.
6. Dopiero po weryfikacji włącz sterowanie falownikiem.

Jeżeli wymagane dane są nieaktualne lub niepoprawne, manager przechodzi do `SAFE MODE` i ogranicza wykonywanie poleceń.

## Brakujące dane

Brak sensora aktualnej ceny lub podstawowego pomiaru instalacji może uruchomić `SAFE MODE`. Brak opcjonalnej prognozy PV nie zatrzymuje integracji, ale ogranicza dokładność planowania.

Jeżeli manager nie reaguje na zmianę progu sprzedaży, należy sprawdzić:

- czy włączony jest **Tryb handlu baterią**,
- czy wskazany sensor pokazuje aktualną cenę sprzedaży w `PLN/kWh`,
- czy SOC jest wyższy od wyznaczonego celu rozładowania,
- czy minimalny przewidywany zysk został osiągnięty,
- czy manager nie działa w `SAFE MODE` albo ochronie awaryjnego SOC.

## Aktualizacje

Nowe wersje są publikowane automatycznie jako wydania GitHub i pobierane przez HACS. Po aktualizacji integracji wymagane jest ponowne uruchomienie Home Assistant.

Przed restartem zalecane jest wykonanie:

```bash
ha core check
```

## Powiązane projekty

- [HomeOn Energy Card](https://github.com/maleikap/homeon-energy-card)
- [Zgłoszenia problemów](https://github.com/maleikap/homeon-energy-manager/issues)
- [Historia zmian](CHANGELOG.md)

## Wsparcie projektu

<div align="center">
  <h3>HomeOn rozwija się dzięki użytkownikom</h3>
  <p>
    Jeżeli HomeOn pomaga lepiej wykorzystywać energię, ograniczać koszty i zarządzać magazynem,<br>
    możesz wesprzeć dalszy rozwój, testy oraz utrzymanie projektu.
  </p>
  <p>
    <a href="https://buycoffee.to/homeon">
      <img src="https://img.shields.io/badge/BuyCoffee-Wesprzyj%20HomeOn-F6C344?style=for-the-badge&logo=buymeacoffee&logoColor=000000" alt="Wesprzyj HomeOn przez BuyCoffee">
    </a>
  </p>
  <p><strong>Dziękuję za każde wsparcie projektu.</strong></p>
</div>
