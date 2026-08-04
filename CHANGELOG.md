# Changelog

## 1.2.5

- Przygotowanie miejsca przed najgorszymi godzinami ponownie używa `Export First` z zablokowanym rozładowaniem baterii, dzięki czemu poranna produkcja PV jest sprzedawana zamiast ładować magazyn.
- `WAIT_BETTER_SELL_PRICE` sprzedaje bieżącą produkcję PV, zachowując energię baterii na późniejszą, lepszą cenę.
- Ładowanie magazynu z PV pozostaje ograniczone do wybranych najgorszych godzin w trybie `PV_LOW_PRICE_CHARGE`.
- Manager nie zmienia `Solar Sell Power` w tych trybach.


## 1.2.4

- W `Zero Export To CT` manager nie zapisuje już encji `Solar Sell Power`; jej wartością zarządza falownik lub użytkownik.
- Manager nadal ustawia tryb pracy i przełącznik `Sell Solar` zależnie od ceny.
- Nastawa mocy eksportu jest zmieniana tylko w `Export First`, podczas świadomej sprzedaży baterii lub przygotowania miejsca przed ceną ujemną.


## 1.2.3

- Zwykłe tryby pracy używają `Zero Export To CT`, dzięki czemu falownik Deye sam rozdziela energię między dom, magazyn i sieć.
- Przy dodatniej cenie manager pozostawia `Sell Solar` włączone i ustawia skonfigurowany maksymalny limit eksportu; przy cenie zerowej lub ujemnej blokuje sprzedaż.
- `Export First` pozostaje wyłącznie dla zaplanowanej sprzedaży energii z baterii i przygotowania miejsca przed cenami ujemnymi.
- Po osiągnięciu celu sprzedaży baterii bieżąca nadwyżka PV może nadal trafić do sieci.


## 1.2.2

- Po zakończeniu wybranych najgorszych godzin manager sprzedaje każdą bieżącą nadwyżkę PV przy dodatniej cenie, zamiast ograniczać produkcję.
- Limit w `PV_PRICE_EXPORT` odpowiada rzeczywistej nadwyżce PV, dzięki czemu brakująca moc nie jest pobierana z baterii.
- Po osiągnięciu celu ładowania cena zerowa lub ujemna nadal blokuje eksport.


## 1.2.1

- Po osiągnięciu docelowego SOC manager jawnie przełącza Deye z `Export First` na `Zero Export To CT`.
- Tryby bez sprzedaży wyłączają eksport, ustawiają limit eksportu na 0 W i nie pozostawiają poprzedniego trybu falownika.
- Sprzedaż baterii kończy się z tolerancją około 1% względem celu zamiast pozostawiać aktywne wymuszenie eksportu.
- Dodano status wykonawczy `DISCHARGE_TARGET_HOLD` dla osiągniętego celu sprzedaży.


## 1.2.0

- Dodano godzinowy optymalizator 24 h wykorzystujący ceny, prognozę PV, godzinowy profil zużycia domu, pojemność baterii i ograniczenia falownika.
- Dodano automatyczną kalibrację prognozy PV na podstawie rzeczywistej produkcji z zakończonych dni.
- Dodano dynamiczny cel SOC, prognozę nadwyżki PV, energię wymaganą do ładowania i plan awaryjny przy niewykonanym ładowaniu.
- Dodano obliczanie mocy i czasu potrzebnego do sprzedaży magazynu oraz możliwość wcześniejszego startu, jeśli najlepsze okno jest zbyt krótkie.
- Kalkulacja uwzględnia sprawność ładowania, sprawność rozładowania, napięcie baterii i koszt cyklu.
- Dodano potwierdzanie wykonania komend Deye: `NEW_PLAN`, `SENT`, `PENDING`, `CONFIRMED` i `NOT_APPLIED`.
- Dodano zdarzenie Home Assistant `homeon_energy_manager_decision` przy zmianie trybu lub statusu potwierdzenia Deye; można je wykorzystać w automatyzacjach i Telegramie.
- Dotychczasowe tryby, zabezpieczenia SOC, ceny ujemne, `SAFE_MODE`, strategia PV i ochrona domu pozostają zachowane.

## 1.1.6

- Uporządkowano kolejność strategii: eksport PV przed najgorszymi godzinami, ładowanie baterii w najgorszych godzinach, oczekiwanie po ich zakończeniu i sprzedaż baterii w najlepszym oknie.
- `PV_PRICE_EXPORT` ma pierwszeństwo przed `WAIT_BETTER_SELL_PRICE`, dopóki wybrane godziny ładowania są jeszcze przed nami.
- `WAIT_BETTER_SELL_PRICE` zachowuje energię baterii, ale sprzedaje bieżącą nadwyżkę PV zamiast kontynuować ładowanie po zakończeniu najgorszych godzin.

## 1.1.5

- W trybie `WAIT_BETTER_SELL_PRICE` nadwyżka PV najpierw ładuje magazyn do 95%, zamiast być sprzedawana po niższej cenie.
- Podczas oczekiwania ładowanie z sieci pozostaje wyłączone, eksport baterii jest zablokowany, a falownik pracuje w `Zero Export To CT`.
- Po osiągnięciu 95% manager może sprzedawać bieżącą nadwyżkę PV, zachowując energię baterii na lepsze okno cenowe.

## 1.1.4

- Manager nie opróżnia baterii po samym przekroczeniu ręcznego progu, jeżeli w ciągu najbliższych 8 godzin występuje wyraźnie lepsza cena sprzedaży.
- Tryb `WAIT_BETTER_SELL_PRICE` zachowuje energię w magazynie, ale nadal sprzedaje bieżącą nadwyżkę PV.
- Dodano kontrolę czasu i minimalnej różnicy ceny, aby nie odkładać sprzedaży dla nieznacznie lepszych lub zbyt odległych okien.

## 1.1.3

- Poprawne wydanie zmian strategii z `1.1.2`; tag `v1.1.2` został utworzony przed aktualizacją koordynatora i nie zawierał kompletnej poprawki.
- Po zakończeniu wybranych tanich godzin manager zamyka okno i może przejść do sprzedaży baterii w najlepszym opłacalnym przedziale.

## 1.1.2

- Zakończone najgorsze godziny nie pozostają aktywne w strategii PV i nie blokują późniejszej sprzedaży magazynu.
- Tryb sprzedaży baterii może rozpocząć się w najlepszym opłacalnym oknie harmonogramu także wtedy, gdy cena jest nieznacznie niższa od ręcznego progu dobrej sprzedaży.
- Powód strategii pokazuje, że wybrane tanie okna zostały zakończone, zamiast nadal wskazywać minione godziny.

## 1.1.1

- Fixed current-hour sell-price handling: an hourly schedule value at `HH:00` now remains active through the full hour.
- EMS decisions use the current schedule interval price and fall back to the entity state only when the schedule has no current interval.
- Added diagnostics showing the effective sell price, raw entity state and selected price source.

W tym pliku dokumentowane są najważniejsze zmiany HomeOn Energy Manager.

## [1.1.0] - 2026-07-31

### Dodano

- automatyczny wybór 2–3 najgorszych godzin ceny sprzedaży w dziennym harmonogramie,
- odkładanie ładowania magazynu na wybrane najgorsze godziny przy dużej prognozie PV,
- tryb `PV_PRICE_EXPORT`, który sprzedaje bieżącą nadwyżkę PV i zachowuje miejsce w magazynie,
- tryb `PV_LOW_PRICE_CHARGE`, który ładuje magazyn z PV w najgorszych godzinach sprzedaży,
- sensory wybranych godzin, statusu, powodu, prognozy i nadwyżki strategii cenowej PV.

### Zmieniono

- liczba godzin ładowania jest dobierana automatycznie do wolnego miejsca oraz prognozowanej średniej mocy PV,
- ładowanie PV ustawia `Zero Export To CT`,
- eksport poza najgorszymi godzinami ustawia `Export First`,
- ładowanie z sieci pozostaje wyłączone podczas ładowania magazynu z PV.

### Bezpieczeństwo

- `SAFE MODE`, awaryjny SOC i ceny ujemne zachowują wyższy priorytet,
- eksport w trybie `PV_PRICE_EXPORT` nie wymusza rozładowania magazynu,
- strategia działa tylko przy włączonym trybie handlu baterią i dostępnym harmonogramie cen.

## [1.0.6] - 2026-07-31

### Poprawiono

- po osiągnięciu ustawionej ceny dobrej sprzedaży manager sprzedaje od razu,
- późniejsza nieco lepsza cena nie przełącza już managera w `WAIT_BETTER_SELL_PRICE`,
- bieżąca nadwyżka PV nie jest ładowana do magazynu, gdy aktualna cena osiągnęła ustawiony próg sprzedaży,
- planner i wykonawca Deye otrzymują tę samą decyzję sprzedaży.

## [1.0.5] - 2026-07-31

### Poprawiono

- stan przełącznika trybu handlu baterią jest odtwarzany z zapisanych opcji po restarcie Home Assistant,
- aktualizacja lub ponowne załadowanie integracji nie wyłącza już samoczynnie wcześniej włączonego handlu,
- domyślna wartość dla nowej instalacji pozostaje bezpiecznie wyłączona.

## [1.0.4] - 2026-07-31

### Poprawiono

- blokada pogodowa nie zatrzymuje już sprzedaży bieżącej nadwyżki PV przy dobrej cenie,
- rezerwa pogodowa nadal chroni baterię przed wymuszonym rozładowaniem,
- eksport PV może działać niezależnie od energii baterii dopuszczonej do sprzedaży.

## [1.0.3] - 2026-07-31

### Poprawiono

- wysoka nadwyżka produkcji PV przy dobrej cenie sprzedaży może uruchomić eksport bez blokady minimalnego zysku liczonego wyłącznie dla baterii,
- `HOME_BATTERY_PRIORITY` nie jest utrzymywany przez histerezę po świadomym włączeniu handlu baterią,
- zachowano blokady sprzedaży dla `SAFE MODE`, awaryjnego SOC, słabej jakości PV i ceny ujemnej,
- dodano diagnostyczny stan możliwości eksportu nadwyżki PV.

## [1.0.2] - 2026-07-31

### Poprawiono

- świadomie włączony tryb handlu baterią nie jest już blokowany tylko dlatego, że bateria jednocześnie zasila dom,
- ochrona zasilania domu pozostaje aktywna, gdy tryb handlu baterią jest wyłączony,
- planner korzysta z aktualnej pojemności magazynu ustawionej encją `number`, a nie ze starej wartości pierwszej konfiguracji,
- obliczenie bezpiecznej energii do sprzedaży używa prawidłowej pojemności magazynu.

## [1.0.1] - 2026-07-31

### Poprawiono

- dobra cena sprzedaży ma pierwszeństwo przed zwykłym tanim ładowaniem,
- zmiana między ładowaniem a sprzedażą nie jest zatrzymywana przez histerezę trybu,
- zachowano nadrzędny priorytet `SAFE MODE`, awaryjnego SOC i ładowania przy cenie ujemnej,
- README otrzymał układ zgodny z HomeOn Energy Card.

## [1.0.0] - 2026-07-31

### Dodano

- edytowalną i trwale zapisywaną pojemność magazynu energii,
- sensor aktualnej energii zgromadzonej w magazynie,
- profesjonalną dokumentację instalacji i wymaganych integracji.

### Poprawiono

- odczyt pojemności magazynu z ustawień zmienianych po pierwszej konfiguracji,
- obliczenia energii dostępnej do sprzedaży, wolnego miejsca i celów SOC po zmianie pojemności,
- rozróżnienie energii znajdującej się w magazynie od wolnego miejsca.

### Bez zmian

- logika sterowania falownikiem Deye,
- zabezpieczenia `dry-run` i `SAFE MODE`,
- planowanie cen, prognozy PV i uczenie zużycia.
