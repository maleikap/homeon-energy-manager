# Changelog

## 1.2.58

- Dzienne pobranie, oddanie, koszt zakupu i wartość sprzedaży są synchronizowane bezpośrednio z Pstryk AIO; obliczenia z mocy CT działają wyłącznie awaryjnie, gdy Pstryk nie udostępnia danego licznika.
- Przy wielu konfiguracjach Pstryk używana jest ta sama końcówka encji (`_2`, `_3` itd.), którą wybrano dla cen. Dane różnych instalacji nie są już mieszane.
- Dodano sensory źródła ceny zakupu i sprzedaży, dzięki którym karta automatycznie wybiera właściwy komplet liczników Pstryk.

## 1.2.57

- Dodano opcjonalną encję obecności sieci lub napięcia fazy do pewnego wykrywania pracy OFF-GRID. Manager nie uznaje samego odczytu `0 W` za awarię sieci.
- W trybie OFF-GRID wyłączane są handel energią, eksport i ładowanie z sieci, a Deye otrzymuje pełny prąd ładowania i rozładowania: PV zasila dom, a nadwyżka ładuje magazyn.
- Zachowano właściwy tryb instalacji: `Zero Export To CT` dla CT oraz `Zero Export To Load` dla LOAD.
- Przy pełnym magazynie nadal działa ochrona ładowania; ograniczenie nadwyżki PV jest wtedy prawidłowe, ponieważ bez sieci nie ma dokąd jej wyeksportować.
- Dodano sensory `Stan połączenia z siecią`, `Źródło stanu sieci` i `OFF-GRID` dla karty oraz automatyzacji.
- Dodano testy zaniku sieci, napięcia `0 V`, obu typów instalacji oraz zabezpieczenie przed fałszywym OFF-GRID przy samym bilansie `0 W`.

## 1.2.56

- Wieczorna decyzja sprzedaży porównuje bieżącą cenę również z cenami następnego poranka z pełnego, 48-godzinnego harmonogramu Pstryk.
- Aktualna integracja `balgerion/ha_Pstryk` jest uzupełniana danymi z `sensor.pstryk_json_buy` i `sensor.pstryk_json_sell`, ponieważ zwykłe sensory ceny bieżącej publikują w atrybucie `All prices` wyłącznie bieżący dzień.
- Obsłużono wiele wpisów Pstryk w jednym Home Assistant. Encje z końcówką `_2`, `_3` itd. są łączone z odpowiadającym im harmonogramem jutra, bez mieszania danych różnych instalacji.
- Dodano test przypadku 0,72 PLN/kWh wieczorem i 1,01 PLN/kWh o 07:00. Manager zachowuje energię i przechodzi w oczekiwanie na lepszą cenę.

## 1.2.55

- Nocne zużycie nie jest już liczone podwójnie przy wyznaczaniu celu ładowania z sieci. Przy dobrej prognozie PV manager nie ustawia z tego powodu celu 95%.
- Przy dobrej, skalibrowanej prognozie PV plan zakupu porównuje ceny nocne z godzinami dziennymi do 16:00 i może zaczekać na tańszą energię.
- Jeżeli magazyn nie dotrwa bezpiecznie do późniejszej tańszej godziny, droższe wcześniejsze okno doładowuje tylko energię pomostową potrzebną do zachowania minimalnego SOC, zamiast realizować cały końcowy cel.
- Dodano testy oczekiwania na tańszą godzinę dzienną oraz ograniczonego nocnego ładowania pomostowego.

## 1.2.54

- Tryb `PV_PRICE_EXPORT` rzeczywiście zatrzymuje ładowanie magazynu i kieruje bieżącą nadwyżkę PV do sieci. Wcześniej planer wybierał sprzedaż, ale pozostawiony prąd ładowania pozwalał Deye nadal ładować baterię.
- Polecenia `No Grid`, `Sell Solar`, wyzerowanie prądu ładowania i właściwy tryb pracy mają pierwszeństwo przed pomocniczymi zmianami Time of Use, więc eksport nie jest odkładany przez limit komend falownika.
- W wybranym późniejszym oknie `PV_LOW_PRICE_CHARGE` manager przywraca skonfigurowany prąd ładowania i uzupełnia tylko zaplanowany brak energii.
- Dodano test zachowania odtwarzający przypadek: PV 4016 W, dom 1431 W, SOC 52%, cena sprzedaży 0,95 PLN/kWh i późniejsze ładowanie po 0,62 PLN/kWh.

## 1.2.53

- Przy dobrej prognozie PV manager nie ładuje magazynu od razu tylko dlatego, że SOC jest niższy od celu. Najpierw sprzedaje bieżącą nadwyżkę w droższej godzinie, a ładowanie PV przenosi do najtańszego przyszłego okna sprzedaży.
- Ilość energii odkładanej do późniejszego ładowania jest liczona z rzeczywistej różnicy między bieżącym SOC a celem, z uwzględnieniem sprawności ładowania. Manager nie planuje już automatycznie ładowania do 95%.
- Plan korzysta wyłącznie z przyszłych godzin cenowych. Zakończone poranne tanie okna nie powodują już błędnego natychmiastowego ładowania baterii.
- Odroczenie jest dozwolone tylko wtedy, gdy pozostała prognozowana nadwyżka PV pokrywa brakującą energię z buforem oraz obecna cena sprzedaży jest co najmniej 0,03 PLN/kWh wyższa od wybranego późniejszego okna.
- Przy słabej prognozie, małej różnicy cen albo braku pełnego harmonogramu manager ładuje magazyn normalnie i zachowuje ochronę rezerwy.

## 1.2.52

- Po północy plan nocnego ładowania korzysta z prognozy PV na bieżący dzień, a nie z prognozy na kolejny dzień. Przy dobrej prognozie kupuje tylko brakującą energię potrzebną do bezpiecznego dotrwania do produkcji PV.
- Manager zapamiętuje ilość energii rzeczywiście naładowanej z sieci oraz jej średni koszt wraz ze stratą ładowania.
- Energia kupiona z sieci nie jest sprzedawana poniżej rzeczywistego kosztu zakupu, strat rozładowania i kosztu cyklu baterii.
- Dodano diagnostykę ilości i kosztu energii kupionej do magazynu oraz minimalnej opłacalnej ceny jej sprzedaży.
- Dodano test przebiegu: zakup po 0,97 PLN/kWh, próba sprzedaży po 0,94 PLN/kWh i dobra prognoza PV.

## 1.2.51

- Celowe rozładowanie magazynu do sieci rozpoczyna się dopiero w najlepszym znanym oknie ceny sprzedaży, z tolerancją 0,01 PLN/kWh.
- Usunięto wcześniejszy start sprzedaży przy 95% najlepszej ceny oraz sprzedaż baterii po samym przekroczeniu stałego progu „dobrej ceny”.
- Dobra prognoza i nadwyżka PV nie pozwalają już opróżniać baterii przed najlepszą ceną. Bieżąca nadwyżka PV nadal może być eksportowana bez rozładowywania magazynu.
- Przygotowanie miejsca przed ceną ujemną również czeka na najlepszą znaną cenę sprzedaży.
- Dodano test przypadku pełnego magazynu, dobrej prognozy PV i ceny 0,98 PLN/kWh przed późniejszą ceną 1,27 PLN/kWh.

## 1.2.50

- Poprawiono wybór aktywnego programu Deye Time of Use. Godzina programu jest początkiem przedziału, więc manager zmienia teraz aktualnie działający wiersz zamiast następnego wiersza z przyszłości.
- Ładowanie z sieci rozpoczyna się w wybranej taniej godzinie i nie jest już przypadkowo przesuwane na późniejszy, droższy przedział.
- Poprawiono obsługę ostatniego programu do północy oraz przejścia przez północ.
- Dodano testy sześciu programów Time of Use dla normalnej pracy, taniego ładowania i ostatniego przedziału dobowego.

## 1.2.49

- Przy SOC bliskim minimalnemu planer nie odkłada już zakupu na późniejszą, droższą godzinę tylko dlatego, że chwilowe zużycie domu jest małe. Uwzględnia bezpieczne minimum poboru i wybiera wcześniejsze tanie okno przed spodziewanym wzrostem ceny.
- Sterownik Deye nadaje pierwszeństwo komendom, które rzeczywiście uruchamiają ładowanie albo udostępniają baterię na potrzeby domu. Aktywny SOC Time of Use nie jest już odkładany poza limit zmian jednego cyklu.
- W normalnej pracy manager natychmiast przywraca `Zero Export To CT` albo `Zero Export To Load`, pełny skonfigurowany prąd rozładowania, `No Grid` i minimalny SOC falownika.
- Dodano testy odtwarzające zakup po 1,35 PLN/kWh mimo dostępnej godziny po 1,09 PLN/kWh oraz import z sieci przy baterii na poziomie 48%.

## 1.2.48

- Ochrona rezerwy przy słabym PV blokuje handel energią z magazynu, ale nie blokuje zasilania domu z baterii.
- Tryby `WEATHER_HOLD_RESERVE` i `PV_REALITY_HOLD` ustawiają Time of Use na minimalny SOC falownika, zachowując `Zero Export To CT` oraz pełny skonfigurowany prąd rozładowania.
- Dodano test zachowania odtwarzający przypadek: PV 586 W, dom 1382 W, bateria 60% i niepotrzebny import z sieci.

## 1.2.47

- Dodano testy zachowania uruchamiające prawdziwy planer i sterownik Deye na atrapach Home Assistanta, w tym pełną symulację 48 godzin.
- Oczekiwanie na lepszą cenę nie jest już automatycznie zamieniane na blokadę rezerwy pogodowej; Time of Use wraca wtedy do minimalnego SOC falownika i bateria może zasilać dom.
- Po przekroczeniu planowanej godziny rezerwy manager nie kupuje drogiej energii tylko z powodu niewielkiej różnicy do celu. Natychmiastowe odzyskiwanie działa dopiero blisko chronionego minimum SOC.
- Dodano scenariusze pompy ciepła o 03:00, niepełnej bieżącej godziny, dobrego PV, sprzedaży w najlepszej cenie, pełnej baterii oraz przywracania ustawień Deye.

## 1.2.46

- Tryb oczekiwania i priorytet domu zawsze przywracają właściwy tryb autokonsumpcji (`Zero Export To CT` albo `Zero Export To Load`) zamiast pozostawiać falownik w poprzednim trybie sprzedaży lub ładowania.
- Poza trybem awaryjnym HomeOn nie ogranicza prądu rozładowania do wartości zastępczej; dom może korzystać z pełnej skonfigurowanej mocy magazynu.
- Sterownik Deye wysyła wyłącznie ustawienia, które rzeczywiście wymagają zmiany, respektuje skonfigurowany odstęp poleceń i bezpiecznie rozkłada duży plan na kolejne cykle.
- Błąd wykonania polecenia nie jest już zapisywany jako poprawnie zastosowany plan.
- Strategia ceny ujemnej korzysta z ustawionych progów zamiast stałych wartości, a przygotowanie magazynu rozpoczyna tylko przy cenie wystarczająco bliskiej najlepszej cenie sprzedaży.
- Dzienne statystyki finansowe po restarcie są inicjalizowane danymi Pstryk AIO zamiast rozpoczynać dzień od zera.
- Usunięto trzy nieużywane progi prognozy PV z konfiguracji oraz nieużywane ustawienie prądu blokady rozładowania.

## 1.2.45

- HomeOn nie obniża już maksymalnego prądu rozładowania baterii do 5 A w trybach ładowania, ochrony rezerwy ani sprzedaży samej nadwyżki PV.
- Ochronę energii w magazynie realizuje cel SOC programu Time of Use, a skonfigurowana moc rozładowania pozostaje dostępna do zasilania domu.
- Sprzedaż samej nadwyżki PV korzysta z `Zero Export To CT`; `Export First` jest używany tylko wtedy, gdy plan rzeczywiście zezwala na sprzedaż energii z baterii.

## 1.2.44

- Po porannym terminie HomeOn nie wymusza od razu ładowania na następny dzień, dopóki nie ma kompletnego harmonogramu cen do kolejnego terminu rezerwy.
- Pominięty termin uruchamia natychmiastowe odzyskanie rezerwy tylko wtedy, gdy bieżący SOC rzeczywiście jest poniżej wymaganego celu.
- Wyjście z `CHEAP_CHARGE` następuje natychmiast po zakończeniu wybranego okna, bez podtrzymywania blokady rozładowania przez histerezę.
- Time of Use otrzymuje cel SOC powiększony o energię przewidywanego zużycia, dzięki czemu aktywne okno naprawdę ładuje zamiast jedynie blokować baterię.
- Podczas oczekiwania falownik wraca do `Zero Export To CT`, wyłącza zakup do magazynu i pozwala baterii zasilać dom.

## 1.2.43

- Nocny plan ładowania uwzględnia energię, którą dom zużyje jeszcze przed godziną wymaganej rezerwy, zamiast porównywać cel wyłącznie z bieżącym SOC.
- Najtańsze godziny są wybierane z wyprzedzeniem, zanim nocne zużycie obniży SOC i wymusi spóźniony zakup energii.
- Rozpoczęta godzina ma pojemność odpowiadającą rzeczywistemu czasowi pozostałemu do jej końca; o 04:55 planer liczy 5 minut, a nie pełną godzinę ładowania.
- Opis planu pokazuje przewidywane zużycie energii do terminu gotowości rezerwy.

## 1.2.42

- HomeOn przewiduje godzinę osiągnięcia bezpiecznej granicy SOC na podstawie energii w magazynie, bieżącego poboru i wyuczonego profilu godzinowego.
- Co najmniej jedno z wybranych okien ładowania musi wystąpić przed przewidywanym wyczerpaniem bezpiecznej rezerwy; manager wybiera najtańszą dostępną godzinę przed tą granicą.
- Poziom awaryjny pozostaje wyłącznie ostatnim zabezpieczeniem, a nie normalnym momentem rozpoczęcia zakupu energii.
- Dodano diagnostykę przewidywanej godziny wyczerpania, bezpiecznej granicy SOC i ładowania wyprzedzającego.

## 1.2.41

- HomeOn nie uruchamia taniego ładowania z sieci, gdy bieżąca nadwyżka PV może ładować magazyn.
- Dobra, skalibrowana prognoza pozostałej produkcji blokuje zakup, jeżeli pokryje brakującą energię magazynu i domu.
- Wyjście z trybu ładowania sieciowego następuje od razu po pojawieniu się wystarczającego PV, bez 10-minutowego podtrzymania trybu.
- W trybie zarabiania dobra bieżąca cena sprzedaży ma pierwszeństwo przed tanim zakupem, jeżeli pracujące PV i prognoza pozwolą później uzupełnić sprzedaną energię.
- Przy potwierdzonym uzupełnieniu z PV magazyn może być bezpiecznie sprzedawany do minimalnego SOC falownika; rezerwa nocna nadal obowiązuje, gdy prognoza lub rzeczywista produkcja tego nie potwierdzają.
- Ładowanie awaryjne i zakup przy cenie ujemnej zachowują pierwszeństwo.

## 1.2.40

- Nocne ładowanie wybiera tanie godziny wyłącznie przed porannym terminem gotowości rezerwy.
- Powtarzalne duże obciążenie nad ranem (np. pompa ciepła) przesuwa termin naładowania przed godzinę jego wystąpienia.
- Jeśli termin został pominięty, a energii nadal brakuje, HomeOn rozpoczyna ładowanie od razu zamiast czekać do kolejnej nocy.

## 1.2.39

- Decyzja o rozładowaniu ustawia w aktywnym programie Time of Use minimalny SOC falownika zamiast dynamicznej rezerwy.
- Dla minimalnego SOC 16% i aktualnego SOC 35% Deye otrzymuje cel 16%, a HomeOn sam zatrzymuje rozładowanie po zmianie decyzji.
- Wyższy cel Time of Use pozostaje używany wyłącznie podczas ładowania oraz świadomego zatrzymania rozładowania.

## 1.2.38

- Każda decyzja sterująca synchronizuje aktywny program Deye Time of Use.
- Po zakończeniu ładowania z sieci HomeOn wyłącza `Grid Charge` w aktywnym slocie i przywraca właściwy cel rozładowania.
- Cel SOC programu jest dobierany osobno dla ładowania, sprzedaży, autokonsumpcji nocnej, ochrony rezerwy i ładowania z PV.

## 1.2.37

- Ładowanie z sieci ustawia teraz aktywny program Deye Time of Use na Grid Charge.
- Docelowy SOC aktywnego programu Time of Use jest synchronizowany z celem wyznaczonym przez HomeOn.
- Dodano diagnostykę numeru aktywnego programu oraz statusu sterowania Time of Use.

## 1.2.36

- Tryb zarabiania uwzględnia prognozowaną nadwyżkę PV jako bezpłatne źródło ponownego uzupełnienia magazynu.
- Koszt zakupu energii po sprzedaży jest liczony wyłącznie dla części, której nie pokryje PV po zabezpieczeniu prognozowanego zużycia domu.
- Dodano diagnostykę pozostałej prognozy PV, pozostałego zużycia domu, uzupełnienia z PV i energii wymagającej odkupienia z sieci.

## 1.2.35

- tryb zarabiania nie wymaga już pełnego magazynu ani SOC 94–95%,
- poranna sprzedaż w godzinach 06:00–10:00 obejmuje energię dostępną ponad dynamiczną rezerwę domu i nocy,
- opłacalność porannej sprzedaży jest liczona względem bieżącej ceny oraz najtańszego późniejszego zakupu,
- do kalkulacji nie jest już używana cena zakupu, która wystąpiła przed sprzedażą,
- tryb zarabiania nie ładuje magazynu z sieci tylko po to, aby ponownie sprzedać energię,
- późniejsze ładowanie z sieci pozostaje zależne od deficytu po uwzględnieniu prognozy PV,
- zachowano minimalny SOC, dynamiczną rezerwę, SAFE MODE oraz ograniczenie synchronizacyjne Deye.

## 1.2.34

- dodano osobny przełącznik `Tryb zarabiania`, działający razem z nadrzędnym zezwoleniem na handel baterią,
- zysk netto uwzględnia cenę sprzedaży, koszt późniejszego zakupu, sprawność ładowania i rozładowania oraz koszt cyklu baterii,
- pełny magazyn jest sprzedawany wyłącznie w najlepszym opłacalnym oknie z dostępnego harmonogramu,
- brakująca energia jest ładowana tylko w najtańszych godzinach przed planowaną sprzedażą,
- zachowano dynamiczną rezerwę domu, rezerwę nocną, minimalny SOC, SAFE MODE i zabezpieczenia Deye,
- dodano sensory diagnostyczne przychodu, kosztów i przewidywanego zysku netto.

## 1.2.33

- dodano wybór typu instalacji `CT` albo `LOAD` w konfiguracji i opcjach integracji,
- instalacja LOAD korzysta bezpośrednio z odczytu LOAD i ustawia `Zero Export To Load`,
- instalacja CT zachowuje dotychczasowy pełny bilans odbiorników oraz `Zero Export To CT`,
- małe ujemne odchylenie mocy LOAD do `-100 W` nie uruchamia już `SAFE MODE`,
- dodano diagnostykę wybranego typu instalacji i źródła mocy domu.

## 1.2.32

- dodano bieżące dzienne liczenie kosztu zakupu i wartości sprzedaży na podstawie mocy CT oraz godzinowych cen Pstryk AIO,
- dodano dzienne liczniki energii importowanej i eksportowanej oraz wynik finansowy,
- statystyki są zapisywane w pamięci integracji i zerowane automatycznie po zmianie dnia,
- przy pierwszej aktualizacji dzisiejsze wartości Pstryk AIO są używane jako punkt początkowy, aby nie zgubić wcześniejszych godzin.
- dodano automatyczne przejście ze starej, niedziałającej integracji Pstryk AIO na sensory `pstryk_current_buy_price` i `pstryk_current_sell_price` z nowego API `unified-metrics`.


## 1.2.31

- rezerwa odłożona na noc jest wykorzystywana przez dom i odbiorniki widoczne za przekładnikami CT,
- w godzinach 20:00–09:00 tryb Zero Export To CT otrzymuje pełny skonfigurowany prąd rozładowania aż do minimalnego SOC,
- ograniczenie 5 A pozostaje aktywne dopiero po osiągnięciu minimalnego SOC, aby zachować synchronizację falownika z siecią,
- wyjście ze starej blokady nocnej nie czeka na zakończenie histerezy trybu.


## 1.2.30

- zakończenie wybranych godzin ładowania nie uruchamia eksportu PV, jeżeli magazyn nie osiągnął jeszcze celu SOC,
- po zakończeniu preferowanych godzin Manager kontynuuje ładowanie z PV do dynamicznego celu,
- eksport bieżącej nadwyżki po zakończeniu godzin jest dozwolony po osiągnięciu celu z tolerancją 1 punktu procentowego.


## 1.2.29

- nocne obciążenie po stronie GRID jest odtwarzane także z już zapisanej historii importu, PV i baterii,
- Manager może uwzględnić wcześniejszą pracę pompy od razu po aktualizacji, bez czekania na kolejną noc,
- rezerwa nocna nadal zachowuje ustawiony margines bezpieczeństwa.


## 1.2.28

- zużycie domu jest liczone z pełnego bilansu PV, sieci i baterii, dzięki czemu obejmuje również pompę podłączoną po stronie GRID za przekładnikami CT,
- profil nocny i plan rezerwy uwzględniają godzinowe zużycie odbiorników niewidocznych na wyjściu LOAD,
- wieczorna sprzedaż pozostawia energię potrzebną na przewidywaną pracę pompy w nocy,
- diagnostyka pokazuje osobno surowy odczyt LOAD oraz całkowite obciążenie obliczone z bilansu CT.


## 1.2.27

- planer handlu łączy teraz bieżący i jutrzejszy harmonogram cen Pstryk AIO,
- wieczorna sprzedaż nie uruchamia się po cenie z końcówki dnia, gdy następnego ranka dostępna jest wyraźnie lepsza cena,
- decyzja planera i diagnostyka najlepszej ceny korzystają z tego samego zestawu danych.


## 1.2.21

- stan encji Pstryk AIO „cena jutro” nie jest już używany jako cena bieżąca, ponieważ jest średnią dobową,
- błędnie wybrana wcześniej encja ceny jutra jest automatycznie mapowana na odpowiadającą encję ceny aktualnej,
- atrybut `tomorrow_prices` nadal jest dołączany do harmonogramu cen na kolejne godziny.


## 1.2.20

- Pstryk AIO jest automatycznie wykrywanym i domyślnym źródłem ceny zakupu oraz sprzedaży,
- harmonogram cen łączy atrybuty `today_prices` i `tomorrow_prices` z osobnych encji Pstryk AIO,
- plan ceny ujemnej korzysta z ceny zakupu, a strategia sprzedaży z ceny sprzedaży,
- ręczny wybór sensora zapisany w opcjach integracji nadal ma pierwszeństwo,
- diagnostyka wskazuje encje będące rzeczywistym źródłem cen.


## 1.2.19

- tryb sprzedaży nadwyżki przy pełnym magazynie działa tylko wtedy, gdy PV rzeczywiście przewyższa zużycie domu,
- przy PV równym 0 W bateria może ponownie zasilać dom zamiast wymuszać import z sieci,
- opis działania nie informuje już o sprzedaży PV, gdy produkcji nie ma.

## 1.2.18

- ochrona pełnego magazynu nie blokuje sprzedaży baterii w najlepszym oknie cenowym,
- tryb `SELL_BATTERY_HIGH_PRICE` ponownie otrzymuje ustawiony prąd rozładowania,
- pełny magazyn nadal nie jest dociskany podczas sprzedaży samej nadwyżki PV.

## 1.2.17

- pełny magazyn przy dodatniej cenie przełącza Deye na `Export First`,
- `Sell Solar` pozostaje włączone, aby falownik nie ograniczał bieżącej produkcji PV,
- prąd ładowania i rozładowania jest ustawiany na 0 A, więc bateria nie jest dociskana ani sprzedawana,
- histereza 95–90% zapobiega częstemu przełączaniu trybów.

## 1.2.16

- podczas oczekiwania na najlepszą cenę bateria może normalnie zasilać dom,
- `Zero Export To CT` i wyłączony `Sell Solar` nadal blokują przedwczesną sprzedaż baterii do sieci,
- drogi import nie jest już wymuszany przez ustawienie prądu rozładowania na 0 A.

## 1.2.15

- usunięto 15-minutową lukę przed najlepszym oknem sprzedaży,
- Manager zachowuje energię w baterii aż do faktycznego rozpoczęcia lepszej ceny,
- bieżący ręczny próg dobrej sprzedaży nie uruchamia już rozładowania w ostatnich 15 minutach oczekiwania.

## 1.2.14

- obniżono bezpieczny próg blokady ładowania do 95% SOC po alarmie nadnapięcia DC,
- ponowne ładowanie jest dozwolone dopiero po spadku SOC do 90%, co usuwa cykliczne skoki produkcji PV,
- ocena słabego PV nie steruje rezerwą przy SOC od 90%, ponieważ ograniczona produkcja może wynikać z pracy falownika, a nie z pogody.

## 1.2.13

- dodano twardą blokadę prądu ładowania 0 A po osiągnięciu 99% SOC,
- blokada pozostaje aktywna do spadku SOC do 97%, aby zapobiec szybkiemu przełączaniu ustawień,
- przy pełnym magazynie ładowanie z sieci jest zawsze wyłączone, a przy dodatniej cenie sprzedawana jest tylko bieżąca nadwyżka PV.

## 1.2.12

- pełny magazyn nie pozostaje w trybie ładowania podczas oczekiwania na lepszą cenę,
- od 99% SOC bieżąca nadwyżka PV jest sprzedawana w `Zero Export To CT` bez celowego rozładowywania baterii,
- chwilowy spadek produkcji PV nie uruchamia ochrony rezerwy przy pełnym magazynie.

## 1.2.11

- oczekiwanie na najlepsze okno sprzedaży działa również wtedy, gdy bieżąca cena jest niższa od ręcznego progu dobrej sprzedaży,
- po zakończeniu najtańszych godzin Manager nie eksportuje PV po niskiej cenie, jeżeli przed nami jest wyraźnie lepsza cena,
- nadwyżka PV doładowuje wtedy magazyn do sprzedaży w korzystniejszym oknie.

## 1.2.10

- podczas oczekiwania na lepszą cenę nadwyżka PV najpierw ładuje magazyn zamiast trafiać do sieci,
- tryb oczekiwania używa `Zero Export To CT`, wyłącza `Sell Solar` i blokuje rozładowanie baterii wartością 0 A,
- ładowanie z sieci pozostaje wyłączone; magazyn jest przygotowywany do sprzedaży w najlepszym oknie cenowym.

## 1.2.9

- diagnostyka Deye nie pokazuje już `unknown`, gdy sterowanie jest celowo wyłączone lub zablokowane,
- encje ustawień `number` i `switch` zostały przeniesione do kategorii konfiguracyjnej,
- dokumentacja wyjaśnia edycję konfiguracji, nazwy trybów Deye i zależność rezerwy nocnej od pojemności magazynu,
- formularz konfiguracji ostrzega o powiązaniu pojemności baterii, zużycia nocnego i marginesu,
- dodano zastrzeżoną licencję zabraniającą kopiowania, modyfikowania i redystrybucji bez pisemnej zgody.

## 1.2.8

- przeliczanie mocy raportowanej w `kW` i `MW` do watów przed użyciem w algorytmie i diagnostyce,
- ostrzeżenie, gdy nocne zużycie z marginesem przekracza pojemność magazynu i blokuje cele SOC,
- wybierana encja trybu pracy falownika oraz konfigurowalne nazwy trybów Deye,
- formularz późniejszej edycji encji i parametrów bez usuwania integracji,
- przygotowanie magazynu przed ujemną ceną korzysta z harmonogramu ceny sprzedaży,
- techniczne sensory zostały przeniesione do kategorii diagnostycznej.

## 1.2.7

- Manager nie zapisuje już nastawy `Solar Sell Power` w żadnym trybie, również podczas sprzedaży baterii i przygotowania miejsca przed ceną ujemną.
- Moc eksportu pozostaje wyłącznie ustawieniem falownika Deye.
- Z formularza nowej instalacji usunięto nieużywaną encję mocy eksportu.
- Tryb pracy, `Sell Solar` oraz ograniczenia prądu baterii nadal są sterowane zgodnie z planem energii.


## 1.2.6

- Manager porównuje bieżącą cenę sprzedaży z najlepszą ceną w pełnym horyzoncie 24 godzin zamiast czekać maksymalnie 8 godzin.
- Wcześniejsze rozpoczęcie rozładowania baterii jest dozwolone tylko przy cenie wynoszącej co najmniej 95% najlepszej ceny.
- Ręczny próg dobrej sprzedaży nie powoduje już sprzedaży magazynu, jeżeli później występuje wyraźnie korzystniejsze okno.
- Bieżąca nadwyżka PV może być nadal sprzedawana podczas oczekiwania bez rozładowywania baterii.


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
