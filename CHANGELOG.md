# Changelog

W tym pliku dokumentowane są najważniejsze zmiany HomeOn Energy Manager.

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
