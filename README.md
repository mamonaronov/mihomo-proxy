# mihomo-proxy

SOCKS5-прокси для Telegram-ботов на одном VPS. Это не бот и не Python: только [Mihomo (Clash Meta)](https://github.com/MetaCubeX/mihomo) в Docker.

Боты ходят в контейнер `proxy` в сети `telegram-proxy`:

```
TELEGRAM_PROXY_URL=socks5://proxy:11808
MIHOMO_API_URL=http://proxy:19090
MIHOMO_API_SECRET=<тот же, что в .env этого проекта>
MIHOMO_PROXY_GROUP=AUTO
```

Порты на хост не публикуются. На той же машине может стоять v2rayN на 10808/10809 — конфликта не будет.

Схема обхода (группы FAST/BACKUP/AUTO, правила) лежит в git. Ссылки подписок и секрет API — только в `.env` (в git не попадает).

## Первый запуск

```bash
cp .env.example .env
# Замени MIHOMO_API_SECRET на свой (например: openssl rand -hex 32)
# URL подписок уже стоят
docker compose up -d --build
```

Доставка обновлений: `git pull && docker compose up -d --build`. Образ на Docker Hub не публикуется.

## Смена подписки

Правишь `SUB3_URL` (или другой `SUBn_URL`) в `.env`, затем:

```bash
docker compose up -d
```

Entrypoint заново подставит yaml. `--build` не нужен.

## Смена схемы групп

Правишь `config.yaml`, коммитишь, на сервере:

```bash
git pull
docker compose up -d --build
```

`--build` нужен, потому что шаблон копируется в образ как `/template/config.yaml`. Живой конфиг mihomo — это `./data/config.yaml` после envsubst, его в git нет.

## Проверка

Не ходи на `127.0.0.1:11808` с хоста — порт не опубликован. Проверяй из сети `telegram-proxy`:

```bash
docker run --rm --network telegram-proxy curlimages/curl:8.5.0 \
  -sS --max-time 8 -x socks5h://proxy:11808 https://api.telegram.org
```

API (секрет берётся из `.env`):

```bash
docker exec mihomo-proxy wget -qO- \
  --header="Authorization: Bearer ${MIHOMO_API_SECRET}" \
  http://127.0.0.1:19090/proxies/AUTO
```

Либо подставь секрет явно:

```bash
source .env
docker exec mihomo-proxy wget -qO- \
  --header="Authorization: Bearer ${MIHOMO_API_SECRET}" \
  http://127.0.0.1:19090/proxies/AUTO
```

## Кэш подписок и deadlock

Провайдеры качаются через группу `SUBSCRIBE`: сначала DIRECT, потом AUTO. Если GitHub закрыт и кэш пустой (первый старт в РФ), подписки не скачаются, пока туннель не поднимется — это deadlock. Volume `./data` лечит это после первого успешного скачивания: дальше работают закэшированные yaml.

Не делай `docker compose down -v` — сотрёшь кэш. `docker compose down` без `-v` кэш в `./data` не трогает.

## Как подключить бота

В compose бота:

```yaml
networks:
  telegram-proxy:
    external: true
    name: telegram-proxy
```

Сервис бота в этой сети. Хост прокси — `proxy`, не `localhost`.

Секрет в `.env` бота (`MIHOMO_API_SECRET`) должен совпасть с `.env` этого проекта.

## Миграция с systemd mihomo на хосте

1. Подними контейнер **рядом** со старым `systemctl`-сервисом (порты контейнера на хост не смотрят, конфликта 11808 не будет).
2. Проверь сеть командой curl выше.
3. Переключи бота на `socks5://proxy:11808` и тот же секрет.
4. Выключи хостовый mihomo: `systemctl disable --now mihomo`.

Пакет mihomo на хост ставить не нужно.

Если переезжаешь со старого хостового mihomo и не хочешь менять `.env` бота, поставь в `.env` этого проекта тот же секрет, что был в yaml:

```
8176598712630598761082765412765789012506456781928765078960
```

Новый инсталл так делать не должен: сгенерируй свой секрет и пропиши его и здесь, и у бота.

## Что где лежит

| Файл | В git | Назначение |
|------|-------|------------|
| `config.yaml` | да | шаблон схемы, плейсхолдеры `${SUB1_URL}` … `${MIHOMO_API_SECRET}` |
| `.env.example` | да | образец переменных, публичные URL уже заполнены |
| `.env` | нет | реальные URL и секрет |
| `./data/config.yaml` | нет | runtime после envsubst |
| `./data/providers/` | нет | кэш подписок mihomo |

`./data` монтируется в `/etc/mihomo`. Тот же каталог ещё раз монтируется в `/root/.config/mihomo` — иначе базовый образ создал бы Docker volume в `/var/lib/docker`.

## Compose бота (напоминание)

Сеть `telegram-proxy` создаёт **этот** проект, у бота она `external: true`.
