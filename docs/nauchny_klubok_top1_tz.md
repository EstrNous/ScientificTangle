# Научный клубок. Техническое задание и план реализации решения уровня топ-1

Версия: 1.0. Назначение: единый рабочий документ для команды из пяти человек и ИИ-агентов. Документ описывает идеальное решение, точку отсечки MVP, расширение до максимального решения, зоны ответственности, синхронизации, контрольные проверки, структуру репозитория, требования к архитектуре, данным, моделям, базам, интерфейсу, эксплуатации, тестированию, демонстрации и сдаче.

Документ создан как практическое ТЗ: его можно положить в репозиторий, использовать как контекст для ИИ-агентов и как основной план работ команды. Язык документа намеренно прямой и операционный: каждый участник должен понимать, что он делает, какие файлы создаёт, от кого зависит, кого блокирует, в какой момент обязан синхронизироваться с командой и по каким признакам задача считается выполненной.

## 1. Цель продукта

Мы строим не чат по документам и не красивую оболочку вокруг векторного поиска. Мы строим доказуемую R&D-карту знаний для горно-металлургических исследований. Система должна превращать статьи, отчёты, доклады, материалы конференций, обзоры, журнальные публикации, патенты, нормативные материалы, справочники, каталоги экспериментов и сведения об экспертах в проверяемую карту знаний.

Пользователь должен иметь возможность задать сложный вопрос на естественном языке и получить не только текстовый ответ, но и таблицу доказательств, ссылки на источники, локальный граф, числовые параметры, географию применения, уровень достоверности, дату актуализации знания, выявленные противоречия, пробелы и рекомендации по дальнейшим шагам.

Идеальный ответ системы должен отвечать на вопрос: что известно, кем и где подтверждено, на каких условиях, с какими числами, из каких источников, как давно это знание обновлялось, где есть конфликт, где есть пробел, кто эксперт и что разумно проверить дальше.

## 2. Цель хакатона

Цель команды — занять первое место. Поэтому решение должно быть не просто рабочим, а демонстрационно сильным, инженерно зрелым и максимально полно закрывающим все пункты условия.

Для топ-1 недостаточно показать чат, который находит похожие фрагменты. Нужно показать продукт, который выглядит как основа промышленной системы: с микросервисной архитектурой, графом знаний, верификацией фактов, источниками до фрагмента или строки таблицы, числовыми фильтрами, географией, ролями доступа, аудитом, экспортом, дашбордами, уведомлениями, оценкой качества и воспроизводимым развёртыванием.

При этом нельзя утонуть в идеальной архитектуре и не успеть собрать end-to-end. Поэтому работа делится на две зоны: обязательный MVP, который должен заработать первым, и максимальное решение, которое наращивается только после прохождения MVP-отсечки.

## 3. Главный принцип работы команды

Сначала мы делаем минимальный, но полноценный end-to-end: загрузка данных, парсинг, извлечение, запись в граф и векторное хранилище, вопрос, план запроса, retrieval, проверка источников, ответ в интерфейсе, демонстрация на официальных вопросах.

После того как MVP стабильно проходит end-to-end тест, мы добавляем улучшения уровня топ-1: расширенная география, версии фактов, review console, manager dashboard, уведомления, экспорт PDF/Markdown/JSON-LD, performance trace, advanced graph view, PCST или его fallback, расширенный аудит и полировка интерфейса.

Запрещено начинать тяжёлые дополнительные функции, пока не пройден MVP. Запрещено ломать контракты без синхронизации. Запрещено писать демо-ответы хардкодом. Запрещено выдавать факт без источника. Запрещено обходить проверку доступа к документам.

## 4. Исходные требования, которые обязаны быть закрыты

Система должна поддерживать сложные многопараметрические запросы: материал, процесс, условия, география, временной диапазон, числовые ограничения, тип источника и уровень достоверности.

Система должна иметь модель верификации знаний: источник, конкретный фрагмент источника, уровень достоверности, статус факта, дата актуализации, версия факта и история изменений.

Система должна различать отечественную и зарубежную практику. География должна пониматься не только как страна публикации, но и как страна применения технологии, регион объекта, страна организации, юрисдикция нормативного документа и место проведения эксперимента.

Система должна поддерживать числовые ограничения и диапазоны: концентрации, температуры, скорости потоков, производительность, технико-экономические показатели, экологические показатели, даты и интервалы.

Система должна масштабироваться на новые технологические домены: гидрометаллургия, пирометаллургия, экология, переработка отходов и последующие направления. Для этого нельзя хардкодить предметные классы в коде. Нужно использовать универсальное ядро, реестр схемы и доменные профили.

Система должна загружать и нормализовать разные типы данных: статьи, обзоры, внутренние отчёты, протоколы экспериментов, таблицы, патенты, нормативные документы, справочники, каталоги экспериментов, список экспертов и лабораторий, тематические теги.

Система должна извлекать сущности, связи, числовые условия, выводы, рекомендации, экспертов, организации, оборудование, материалы, процессы, свойства, источники и алиасы.

Система должна строить граф знаний, поддерживать сложные обходы связей, хранить версии фактов, обновлять знания при появлении новых источников и подсвечивать противоречия.

Система должна давать пользователю понятный интерфейс: чат, поиск с фильтрами, таблицу доказательств, источник, локальный граф, пробелы, конфликты, экспертов, дашборды, экспорт.

Система должна учитывать безопасность: роли пользователей, уровни доступа документов, аудит запросов, просмотров и экспорта, ограничения для внешних партнёров.

Система должна быть быстрой: сложный запрос по предобработанной базе должен возвращать начальный ответ и основные evidence-блоки за 3–5 секунд при целевой архитектуре до 1 млн сущностей. Полная генерация расширенного ответа может стримиться, но retrieval и доказательная часть должны быть спроектированы под быстрый ответ.

## 5. Официальные сценарии, на которых обязано держаться демо

Первый официальный сценарий: методы обессоливания воды для обогатительной фабрики при составе воды: сульфаты, хлориды, Ca, Mg, Na по 200–300 мг/л, требуемый сухой остаток не более 1000 мг/дм³. Система должна распарсить состав, понять диапазоны, найти методы, сравнить применимость, показать источники и ограничения.

Второй официальный сценарий: технические решения организации циркуляции католита при электроэкстракции никеля и оптимальная скорость потока. Система должна найти решения в мировой практике, сопоставить синонимы, выделить оборудование, условия, скорость потока, источники и возможные разногласия.

Третий официальный сценарий: эксперименты и публикации по распределению Au, Ag и МПГ между медным или никелевым штейном и шлаком за последние 5 лет. Система должна применить временной фильтр, найти элементы и группы элементов, различить штейн и шлак, вернуть таблицу экспериментов и публикаций.

Четвёртый официальный сценарий: способы закачки шахтных вод в глубокие горизонты в России и за рубежом и их технико-экономические показатели. Система должна различить отечественную и зарубежную практику, найти географию применения, показатели стоимости, производительности, ограничений и рисков.

Пятый демонстрационный сценарий для топ-1: показать пробел в знаниях, например комбинацию холодный климат, кучное выщелачивание, никелевая руда, выход металла. Система должна объяснить, что именно не найдено, какие близкие кейсы есть и какие эксперты или лаборатории связаны со смежной темой.

Шестой демонстрационный сценарий для топ-1: показать конфликт или слабую доказательность. Система должна найти два источника с несовпадающими значениями или выводами, показать условия каждого источника и не смешивать разные условия как прямой конфликт.

## 6. Точка отсечки MVP

MVP считается готовым только тогда, когда команда может пройти полный end-to-end без ручных действий в базе и без консольных правок в момент демо.

MVP должен включать загрузку набора файлов или ZIP, сохранение исходников, парсинг текстов и таблиц, создание NormalizedDocument, создание SourceSpan, загрузку справочников, извлечение базовых сущностей, извлечение числовых параметров, построение claims, запись в Neo4j, индексацию фрагментов и строк таблиц в Qdrant, построение Query IR, гибридный поиск, точный графовый поиск, табличный поиск, объединение результатов, проверку источников, генерацию ответа, отображение таблицы, источников и локального графа в интерфейсе.

MVP обязан отвечать хотя бы на четыре официальных вопроса в базовом виде. Ответ может быть не идеальным по красоте, но должен быть доказуемым: каждая ключевая строка ответа должна иметь источник, числовые значения должны быть выделены, география должна быть хотя бы на уровне отечественная, зарубежная, неизвестно, а unsupported claims должны быть явно помечены.

MVP обязан иметь минимальный контроль доступа: роли администратора, исследователя и внешнего партнёра; уровень доступа документа; запрет показывать источник и факт пользователю, если у него нет доступа к исходному документу.

MVP обязан иметь audit log: кто задал запрос, когда, какой был вопрос, какие источники открывались, был ли экспорт. Для MVP достаточно PostgreSQL-таблицы и простой админской страницы или API.

MVP обязан иметь воспроизводимый запуск: docker compose, .env.example, Makefile, README, seed demo data, reset script, healthchecks.

Если хотя бы один из этих пунктов не работает, команда не имеет права считать MVP готовым и переходить к полировке.

## 7. Максимальное решение после MVP

После прохождения MVP команда делает функции, которые создают эффект решения первого места: расширенное сравнение технологий, advanced gap/conflict analysis, полноценный review console, manager dashboard, пользовательские интересы и уведомления, экспорт PDF/Markdown/JSON-LD, performance trace, расширенный аудит, улучшенный source viewer, красивый локальный граф, обработку версий фактов, delta ingestion, отчёт evaluation и стабильный demo mode.

Максимальное решение должно выглядеть как продукт, а не как набор скриптов. В интерфейсе должны быть видны: загрузка и статус обработки данных, чат, поиск с фильтрами, источники, таблицы, локальный граф, пробелы, конфликты, эксперты, дашборд покрытия знаний, профиль интересов, уведомления, экспорт, админские настройки доступа и аудит.

Приоритет максимального решения такой: сначала функции, прямо закрывающие требования условия, затем функции, усиливающие демонстрацию, затем украшения интерфейса.

## 8. Продуктовые принципы

Первый принцип: evidence-first. Нельзя выдавать факт как подтверждённый, если у него нет источника и SourceSpan. Если факт найден моделью, но источник слабый или отсутствует, он становится candidate и показывается как неподтверждённый.

Второй принцип: не “истина в графе”, а claim-based знание. Граф хранит не абсолютные утверждения, а claims, observations и measurements, привязанные к источникам, условиям, методам, датам и confidence.

Третий принцип: открытая схема. Код знает универсальные типы, а конкретные предметные типы приходят из реестра схемы, справочников и доменного профиля. Новые сущности и классы попадают в candidate layer и могут быть подтверждены экспертом.

Четвёртый принцип: гибридный поиск. В задаче нельзя полагаться только на dense embeddings. Нужны графовый поиск, лексический поиск, поиск по таблицам, поиск по источникам, алиасы, точные совпадения формул и числовые фильтры.

Пятый принцип: Query IR вместо свободного Cypher. Модель не должна писать произвольный Cypher как основной путь. Она строит типизированный план запроса, который исполняется контролируемыми операциями backend и базы.

Шестой принцип: локальный граф ответа вместо полного графового хаоса. Пользователю показывается компактный доказательный граф по конкретному вопросу, а не миллион узлов.

Седьмой принцип: доступ проверяется до синтеза ответа. Нельзя сначала собрать ответ из закрытых документов, а потом пытаться скрыть ссылки. Retrieval должен учитывать роль пользователя и доступные документы.

Восьмой принцип: производительность проектируется заранее. Нельзя пытаться выполнить тяжёлую модельную обработку в момент каждого запроса. Всё, что можно посчитать заранее, считается на ingestion.

## 9. Дата актуализации факта и версионирование

Дата актуализации факта не равна только дате последнего эксперимента. В системе нужно хранить несколько дат, потому что научное знание живёт в нескольких временных слоях.

Дата эксперимента показывает, когда было проведено наблюдение или опыт. Дата источника показывает, когда статья, отчёт, патент или протокол зафиксировали это знание. Дата загрузки показывает, когда система получила источник. Дата извлечения показывает, когда claim был создан системой. Дата экспертной проверки показывает, когда человек подтвердил или отклонил claim. Дата актуализации показывает, когда система последний раз пересобрала или переоценила claim с учётом всех доступных источников.

Для каждого claim должны храниться поля: claim_id, claim_version, status, confidence, source_span_ids, experiment_performed_at, source_published_at, source_ingested_at, claim_extracted_at, claim_last_reviewed_at, claim_last_updated_at, latest_supporting_evidence_date, supersedes_claim_id, updated_reason.

Статусы факта: extracted, candidate, auto_verified, verified, conflicting, deprecated, rejected. Ответ может опираться только на auto_verified или verified claims. Candidate можно показывать отдельно с предупреждением. Conflicting должен попадать в блок противоречий. Deprecated нельзя выдавать как актуальный факт.

Версия факта обновляется при появлении нового источника, экспертной правке, изменении confidence, обнаружении конфликта, изменении источника или изменении схемы. История версий должна сохраняться, чтобы можно было объяснить, почему вывод поменялся.

## 10. Нормализация данных

Нормализация данных означает не “почистить текст”, а привести все входные материалы к единому внутреннему формату. Это обязательный слой, без которого граф знаний будет несогласованным.

Каждый входной файл превращается в NormalizedDocument. В нём есть document_id, title, source_type, source_path, folder_category, language, metadata, blocks, tables, figures, attachments, access_level, parse_warnings и source_spans.

Текстовые фрагменты превращаются в DocumentBlock. Таблицы превращаются в TableBlock с ячейками, строками, заголовками, единицами измерения по колонкам и cell-level provenance. Источники превращаются в SourceSpan с указанием документа, страницы, листа, таблицы, строки, колонки, диапазона символов, сырого текста и распарсенного текста.

Числа превращаются в Quantity: raw_text, operator, value, min, max, unit, normalized_value, normalized_unit, uncertainty, dimension, parser_confidence. Важно хранить оператор: меньше, больше, не более, диапазон, около, среднее, медиана.

География превращается в GeoContext: source_country, practice_country, facility_location, organization_country, regulatory_jurisdiction, geo_precision, geo_confidence.

Доступ превращается в AccessPolicy: public, internal, confidential, restricted, allowed_roles, owner_team, export_allowed.

## 11. Реальная онтология

Нужна реальная онтология, но не тяжёлая академическая OWL-система ради галочки. Для хакатона нужна операционная онтология: реестр типов сущностей, типов отношений, атрибутов, правил валидации, алиасов, справочников, версий и доменных профилей.

Универсальное ядро содержит EntityType, RelationType, AttributeType, EntityInstance, RelationInstance, Claim, Observation, Measurement, SourceSpan, SchemaVersion, ValidationRule, ReviewDecision.

Доменный профиль “горно-металлургические R&D” загружается поверх универсального ядра. Он содержит стартовые типы: Material, Substance, Process, Equipment, Property, Experiment, Publication, InternalReport, Patent, Standard, Expert, Lab, ResearchTeam, Facility, TechnologySolution, Geography, EconomicIndicator, EnvironmentalIndicator, Recommendation.

Справочники материалов, оборудования, свойств, единиц измерения, сотрудников, лабораторий и тематических тегов используются как seed layer. Они не хардкодятся в Python-классы. Они загружаются как данные в Schema Registry и используются для entity linking, alias mining, validation, confidence policy и фильтрации.

Предметные категории вроде руда, шлак, штейн, католит, анолит, шахтная вода, газ, реагент, техногенный гипс не должны быть жёсткими классами в коде. Они должны быть значениями классификации или кандидатами в доменном профиле. Так система сможет расширяться на новые домены без переписывания архитектуры.

Минимальные отношения: uses_material, operates_at_condition, produces_output, described_in, validated_by, contradicts, measured_in, authored_by, expert_in, applied_in_geography, uses_equipment, has_economic_indicator, has_environmental_indicator, updates, supersedes.

## 12. Архитектура решения

Целевая архитектура микросервисная. На хакатоне допускается разумное упрощение внутри репозитория, но сервисные границы должны быть реальными: отдельные директории, отдельные API, отдельные зоны ответственности, независимые healthchecks и логи.

UI Service отвечает за интерфейс: чат, поиск, загрузку, source viewer, локальный граф, таблицы, review console, dashboard, admin, profile, notifications, exports.

API Gateway / BFF отвечает за внешние API, валидацию DTO, request_id, streaming, авторизацию на входе, маршрутизацию, нормализацию ошибок и агрегацию payload для UI.

Auth / Security / Audit Service отвечает за роли, access policy, audit log, правила доступа, настройки администратора, retention policy и проверку прав на источник.

Orchestrator Service отвечает за пайплайны ingestion, query, review, evaluation, export, notification. Он хранит состояние задач, запускает этапы, делает retries, timeouts и fallback.

Ingestion Service отвечает за загрузку, парсинг, NormalizedDocument, TableBlock, SourceSpan, классификацию source_type, извлечение метаданных, сохранение исходников и отчёт обработки.

Knowledge Service отвечает за Schema Registry, доменный профиль, справочники, извлечение сущностей и связей, алиасы, entity resolution, нормализацию единиц, построение claims, версии фактов и запись в граф.

Retrieval Service отвечает за Query IR, retrieval plan, entity linking, graph exact search, dense search, sparse search, table search, numeric interval search, geo filter, fusion, reranking, evidence verification, gaps, conflicts и EvidenceBundle.

Model Service отвечает за LLM, embeddings, reranking, structured extraction, prompt templates, model routing, timeouts, fallback, caching и structured output validation.

Export Service отвечает за Markdown, PDF, JSON, JSON-LD и evidence bundle. Для MVP может быть модулем backend, для максимального решения — отдельным сервисом.

Notification Service отвечает за профиль интересов пользователя, сопоставление новых источников с интересами, уведомления в интерфейсе и, при наличии времени, email/webhook.

Neo4j хранит граф знаний, schema registry, сущности, отношения, claims, measurements, source span metadata, candidates, review decisions, versions.

Qdrant хранит векторы document chunks, source spans, table rows, captions, conclusions, payload-ссылки на graph ids и source span ids.

PostgreSQL хранит пользователей, роли, audit log, ingestion tasks, query runs, exports, notifications, user interests, service state и административные настройки.

Object Storage хранит исходные файлы, нормализованные артефакты, экспортированные отчёты, демо-архивы и временные файлы. Для локального запуска используется MinIO или файловая папка с совместимым интерфейсом.

Redis или очередь задач используется для фоновых задач, статусов, блокировок, кэша и ограничения нагрузки. Если времени мало, MVP может использовать PostgreSQL + background workers, но интерфейс очереди должен быть выделен.

## 13. Поток ingestion

Пользователь загружает файл, набор файлов или ZIP. Gateway проверяет права, создаёт ingestion task и отдаёт task_id. Orchestrator запускает ingestion pipeline.

Ingestion Service сохраняет исходные файлы, определяет типы, распаковывает ZIP, сохраняет исходную структуру папок и метаданные. Структура папок вроде “Доклады”, “Журналы”, “Материалы конференций”, “Обзоры”, “Статьи” используется как подсказка source_type, но не как единственный источник истины.

Дальше Ingestion Service строит NormalizedDocument. Для PDF, DOCX, PPTX, XLSX, CSV, TXT, Markdown и HTML должны быть отдельные адаптеры или fallback. Scans и изображения не являются must-have, но должны сохраняться как figures metadata с parse warning.

Таблицы обрабатываются отдельным модулем. Он восстанавливает заголовки, определяет multi-row headers, выделяет единицы измерения, различает служебные строки и строки экспериментов, создаёт SourceSpan до уровня ячейки.

Knowledge Service получает normalized artifacts и запускает schema-aware extraction, open extraction, alias mining, entity resolution, unit normalization, geo extraction, date extraction, claim building, conflict marking и version update.

После этого Knowledge Service пишет сущности, отношения, claims и metadata в Neo4j. Retrieval Service или ingestion worker индексирует chunks, source spans и table rows в Qdrant.

В конце формируется ingestion report: документов обработано, таблиц извлечено, SourceSpan создано, сущностей найдено, aliases найдено, claims создано, candidates создано, conflicts найдено, ошибок парсинга, документов без доступа, документов без даты, среднее время обработки.

## 14. Поток query

Пользователь задаёт вопрос в чате или в поиске с фильтрами. Gateway создаёт query run, проверяет роль пользователя, добавляет request_id и передаёт вопрос в Orchestrator.

Retrieval Service строит Query IR. В Query IR должны быть goal, entities, materials, substances, processes, equipment, conditions, numeric_constraints, geo_scope, time_range, source_types, access_scope, output_format, analysis_flags, confidence_threshold.

Entity Linking связывает mentions из вопроса с canonical entities и aliases. Важно поддерживать аббревиатуры, химические формулы, русско-английские соответствия, транслитерацию и сокращения из справочников.

Retrieval plan запускает параллельно dense search, sparse search, table search, graph exact search, evidence retrieval, numeric interval filter и geo filter. GraphExact зависит от entity linking, но raw dense/sparse/table search может стартовать сразу.

Fusion объединяет результаты, нормализует score, применяет веса, делает reranking и собирает EvidenceBundle. EvidenceBundle содержит verified_claims, candidate_claims, source_spans, tables, graph_subgraph, conflicts, gaps, warnings, retrieval_trace.

Evidence verification удаляет или понижает факты без источника, факты без доступа для текущего пользователя, факты с низкой уверенностью, устаревшие факты и claims без SourceSpan.

Answer Synthesis получает только EvidenceBundle, а не весь корпус. Ответ должен содержать краткий вывод, таблицу, источники, confidence, warnings, локальный граф, gaps, conflicts, experts, recommended follow-ups и export links.

## 15. Производительность

Цель: по предобработанной базе первый доказательный ответ должен появляться за 3–5 секунд. Под “первым доказательным ответом” понимается короткий вывод, таблица основных evidence, источники и статус выполнения. Расширенная формулировка может продолжать стримиться.

Для этого ingestion должен считать тяжёлые вещи заранее: embeddings, source spans, entities, aliases, measurements, claims, graph indexes и table row indexes. В момент запроса нельзя заново парсить документы или заново извлекать сущности из всего корпуса.

Бюджет времени: до 300 мс на приём запроса и проверку доступа; до 700 мс на Query IR и entity linking; до 1200 мс на параллельный graph/vector/table retrieval; до 800 мс на fusion и evidence verification; до 1000 мс на начальный synthesis и streaming.

PCST, расширенный локальный граф, глубокий обзор литературы и рекомендации не должны блокировать первый ответ. Если PCST не успевает за таймаут, используется GraphNeighborhood fallback.

Обязательные технические меры: индексы Neo4j, payload indexes Qdrant, кэш aliases, кэш Query IR для повторных вопросов, ограничение top-k, timeouts на каждый retriever, request tracing, p50/p95 latency metrics.

## 16. Безопасность и аудит

Роли MVP: admin, researcher, analyst, manager, external_partner. Для максимального решения добавляются project_owner, reviewer, auditor.

Каждый документ имеет access_level: public, internal, confidential, restricted. У документа есть allowed_roles, owner_team, export_allowed и retention_policy.

Каждый запрос выполняется с access_scope текущего пользователя. Retrieval не должен возвращать source spans из документов, к которым пользователь не имеет доступа. Если ответ опирается только на закрытые источники, пользователь получает сообщение о недостатке прав, а не пересказ закрытого содержания.

Audit log должен фиксировать query_created, answer_generated, source_opened, document_uploaded, document_exported, review_decision, access_denied, admin_setting_changed. Для каждого события хранится user_id, role, action, object_type, object_id, request_id, timestamp, ip/session, status.

В админской панели должны быть минимальные настройки: роли, уровни доступа, какие действия логировать, сколько хранить логи, разрешён ли экспорт, какие роли видят конфиденциальные документы.

## 17. Экспорт

MVP должен поддерживать экспорт Markdown и JSON. Максимальное решение должно поддерживать PDF и JSON-LD.

Экспорт должен включать answer_text, evidence_table, source_links, graph_subgraph, gaps, conflicts, confidence_summary, query_ir, retrieval_trace, generation_timestamp, user_role, access_scope и предупреждения.

PDF нужен для презентаций и технических заданий. Markdown нужен для Git, README и быстрой передачи результатов. JSON-LD нужен как демонстрация совместимости с онтологическим и FAIR-подходом.

Экспорт закрытых источников должен проверять права. Если пользователь не имеет права на источник, экспорт должен либо исключить этот источник, либо отказать в экспорте.

## 18. Уведомления и профиль интересов

MVP может ограничиться простым профилем интересов и уведомлениями в интерфейсе. Пользователь в профиле пишет интересы на естественном языке, например “электроэкстракция никеля, циркуляция католита, обессоливание шахтных вод”. Система извлекает сущности и сохраняет user_interest_profile.

При добавлении новых документов Notification Service сопоставляет новые entities, claims и tags с профилем интересов пользователя. Если есть совпадение, создаётся уведомление: появился новый источник по теме, найден новый эксперимент, найден конфликт с прежним выводом, появился новый кандидат на alias.

Для топ-1 фича должна быть видна в интерфейсе: иконка уведомлений, список уведомлений, ссылка на источник, объяснение почему это может быть интересно.

## 19. Дашборды

Manager dashboard показывает покрытие знаний по направлениям: гидрометаллургия, пирометаллургия, экология, переработка отходов, водоочистка, электроэкстракция, газоочистка, переработка отходов.

Показатели дашборда: количество документов, количество claims, количество verified claims, количество candidates, количество gaps, количество conflicts, распределение по годам, распределение по географии, активные лаборатории, эксперты, темы с низким покрытием, темы с высоким числом противоречий.

Evaluation dashboard показывает official questions, expected vs actual, найденные источники, missing evidence, unsupported claims, numeric correctness, source citation coverage, latency.

Ingestion dashboard показывает очередь загрузок, статус документов, ошибки парсинга, количество таблиц, количество source spans, количество извлечённых сущностей и claims.

## 20. Репозиторий

Репозиторий должен быть понятен человеку и ИИ-агенту. Каждый сервис имеет README, Dockerfile, tests, src, pyproject или package config, healthcheck и API contracts.

Рекомендуемая структура:

repo/
  README.md
  Makefile
  docker-compose.yml
  docker-compose.prod.yml
  .env.example
  .gitignore
  docs/
    00_product_vision.md
    01_compliance_matrix.md
    02_architecture.md
    03_ontology.md
    04_data_contracts.md
    05_api_contracts.md
    06_demo_script.md
    07_submission_checklist.md
    08_agent_context.md
  agent_context/
    common_system.md
    frontend.md
    backend.md
    ml.md
    sre.md
    database.md
    review_rules.md
  shared/
    contracts/
    utils/
    logging/
    config/
  services/
    gateway/
    auth_audit/
    orchestrator/
    ingestion/
    knowledge/
    retrieval/
    model/
    export/
    notification/
  ui/
  infra/
    docker/
    base-images/
    neo4j/
    qdrant/
    postgres/
    minio/
    nginx/
    monitoring/
    scripts/
  ontology/
    core_schema.yaml
    domain_pack_mining_metallurgy.yaml
    validation_rules.yaml
  dictionaries/
    materials/
    equipment/
    properties/
    units/
    experts/
    tags/
  eval/
    gold_questions.json
    expected_answers/
    run_eval.py
    reports/
  demo/
    seed_data/
    official_questions.md
    demo_script.md
    screenshots/
  tests/
    e2e/
    integration/
    performance/

В agent_context должны лежать единые системные инструкции для ИИ-агентов. Каждый разработчик даёт агенту common_system.md, свой role-файл, текущий service README, contracts и конкретную задачу. Агенту запрещено менять shared contracts, API contracts, ontology или domain pack без явного решения команды на sync point.

## 21. Среды и сборка

Должны быть минимум две среды: local и demo/prod. Local запускается одной командой и нужен всем разработчикам. Demo/prod нужен для сдачи и внешнего тестирования жюри.

SRE отвечает за docker-compose, базовые образы, multistage build, healthchecks, volumes, network, env profiles, Makefile, CI, deploy, logs, monitoring.

Для тяжёлых ML-зависимостей используется base image. Базовый образ содержит системные зависимости, Python, CUDA-зависимости при необходимости, основные библиотеки, OCR-зависимости только если нужны, общие ML-библиотеки. Код сервиса копируется отдельным слоем, чтобы изменения кода не пересобирали тяжёлые зависимости.

Makefile должен содержать команды: make up, make down, make build, make seed, make ingest-demo, make e2e, make eval, make perf-smoke, make reset-demo, make logs, make lint, make test, make export-demo.

Каждый сервис имеет /health, /ready и /metrics. Gateway показывает сводную страницу здоровья всех сервисов.

## 22. Роли команды

Команда состоит из пяти человек: фронтендер, ML-инженер, SRE, бэкендер, инженер баз данных. Все помогают друг другу, но каждый имеет зону владения и конечные deliverables.

Фронтендер отвечает за интерфейс, сценарии пользователя, демонстрацию результата и визуальную убедительность. Его нельзя блокировать ожиданием настоящего backend: backend обязан дать mock payload и OpenAPI как можно раньше.

ML-инженер отвечает за извлечение, модели, embeddings, prompts, structured outputs, оценку качества извлечения, reranking и gold dataset вместе с командой.

SRE отвечает за запуск, сборку, окружения, деплой, CI, Makefile, Docker, base images, monitoring, logs, reset scripts, demo reliability.

Бэкендер отвечает за API Gateway, Orchestrator, ingestion endpoints, query pipeline orchestration, security/audit endpoints, export, notification и интеграционные тесты.

Инженер баз данных отвечает за Neo4j, Qdrant, PostgreSQL, объектное хранилище, индексы, миграции, graph operations, payload indexes, performance и data contracts на уровне хранения.

## 23. Задачи фронтендера

MVP-задачи фронтендера: собрать каркас UI, подключить Gateway, сделать экран загрузки, экран чата, отображение markdown/table ответа, блок источников, локальный граф, ingestion status, простую страницу поиска с фильтрами, простую страницу audit/admin или хотя бы отображение роли пользователя.

Компоненты MVP: ChatPage, UploadPage, SearchPage, SourceViewer, EvidenceTable, LocalGraph, IngestionDashboard, Layout, RoleSwitcher, AnswerRenderer, WarningsPanel.

Top-1 задачи фронтендера: ReviewConsole, GapConflictView, ManagerDashboard, EvaluationDashboard, NotificationBell, UserInterestsProfile, ExportPanel, красивый SourceSpan highlighter, graph legend, retrieval trace viewer, admin access settings.

Синхронизация фронтендера с backend обязательна на этапе фиксации AnswerPayload, SourceSpanPayload, GraphSubgraphPayload, IngestionTaskPayload, SearchResultPayload, UserRolePayload, ExportPayload.

Definition of Done для UI: пользователь понимает систему за 30 секунд; demo flow проходит без консоли; таблицы читаются; источники открываются; граф не превращается в кашу; ошибки показываются нормально; loading states есть; при падении сервиса интерфейс не ломается.

## 24. Задачи ML-инженера

MVP-задачи ML-инженера: выбрать embedding model, настроить Model Service, сделать structured extraction prompts, настроить entity extraction, relation extraction, measurement extraction, alias extraction, Query IR extraction, answer synthesis, reranking или простой scoring, gold questions и eval метрики.

ML должен обеспечить извлечение материалов, веществ, процессов, оборудования, свойств, числовых параметров, единиц, дат, географии, экспертов, источников, выводов и рекомендаций. На MVP допускается schema-aware extraction плюс rule-based extraction для чисел и единиц.

ML должен сделать alias mining: сокращения в скобках, русско-английские соответствия, транслитерация, нормализация дефисов, химические формулы, fuzzy matching, справочники, embedding similarity. Ручной словарь не является основной стратегией, но справочники используются как seed layer.

ML должен сделать Query IR так, чтобы не терялись числовые ограничения, география и временной диапазон. Для официальных вопросов должны быть сохранены все ключевые constraints.

Top-1 задачи ML: candidate schema extraction, conflict detection logic, gap suggestions, recommendation prompts, user interest extraction, notification matching, JSON-LD export enrichment, prompt versioning, model fallback, evaluation dashboard data.

Definition of Done для ML: structured outputs валидируются JSON schema; unsupported claim rate измеряется; numeric correctness проверяется; Query IR корректен на 4 официальных вопросах; extraction не пишет claims без SourceSpan; prompts лежат в репозитории и версионируются.

## 25. Задачи SRE

MVP-задачи SRE: создать репозиторный каркас, docker-compose, base images, Makefile, .env.example, healthchecks, volumes, локальную сеть сервисов, nginx или простой gateway routing, PostgreSQL, Neo4j, Qdrant, MinIO, Redis, логи, reset scripts, seed scripts.

SRE должен сделать multistage build: отдельный слой зависимостей, отдельный слой кода, отдельный runtime stage. Для ML-сервисов нужен base image, чтобы тяжёлые зависимости не пересобирались при каждой правке кода.

SRE должен сделать команды для команды: make up, make down, make build, make seed, make ingest-demo, make e2e, make eval, make perf-smoke, make logs, make reset-demo. Эти команды должны работать на чистой машине при наличии .env.

Top-1 задачи SRE: CI pipeline, deploy на облако, HTTPS или reverse proxy, monitoring, structured logs, request_id propagation, metrics, backup demo data, release archive, submission artifacts, uptime на время защиты.

Definition of Done для SRE: вся система поднимается одной командой; health page зелёная; logs доступны; reset demo работает; seed demo data загружается; deploy-ссылка открывается; падение одного сервиса понятно диагностируется.

## 26. Задачи бэкендера

MVP-задачи бэкендера: Gateway endpoints, Orchestrator pipelines, upload API, task status API, query API, source API, graph API, search API, auth stub, audit API, export Markdown/JSON, notification stub, DTO validation, error handling, request_id.

Бэкендер должен реализовать основной поток: POST /api/documents/upload, GET /api/tasks/{id}, POST /api/query, GET /api/runs/{id}, GET /api/source/{source_span_id}, GET /api/graph/subgraph, GET /api/search, POST /api/export.

Бэкендер вместе с ML и DB реализует пайплайн: ReceiveQuestion, ExtractIntent, BuildQueryIR, EntityLinking, BuildRetrievalPlan, RunRetrievers, Fusion, EvidenceVerification, AnswerSynthesis, ReturnAnswerPayload.

Бэкендер отвечает за то, чтобы AnswerPayload был стабильным для UI. Если backend ещё не готов, должен быть mock API с тем же payload.

Top-1 задачи backend: review decision API, admin settings API, notification API, user interests API, evaluation API, retrieval trace API, PDF export API, access-aware retrieval integration.

Definition of Done для backend: OpenAPI актуален; DTO совпадают с shared contracts; ошибки нормализованы; запросы логируются; каждый endpoint имеет тест; UI может работать по mock и по real API без изменения кода.

## 27. Задачи инженера баз данных

MVP-задачи DB-инженера: создать Neo4j схему, индексы и constraints; создать Qdrant collections и payload indexes; создать PostgreSQL миграции; описать graph operations; реализовать write/read adapters; подготовить seed dictionaries; обеспечить performance на demo corpus.

Neo4j должен хранить EntityType, RelationType, Entity, Relation, Alias, Claim, Observation, Measurement, Experiment, Document, SourceSpan metadata, CandidateEntity, CandidateRelation, CandidateClass, ReviewDecision, SchemaVersion, FactVersion.

Qdrant должен хранить document chunks, table rows, source spans, captions, conclusions, dense vectors, sparse vectors или lexical payload, document metadata, source_span_id, graph_entity_ids, claim_ids, access_level и source_type.

PostgreSQL должен хранить users, roles, permissions, audit_events, ingestion_tasks, query_runs, export_jobs, notifications, user_interests, admin_settings, service_state.

DB-инженер должен сделать graph operations: find_entities, resolve_aliases, expand_neighbors, filter_by_constraints, aggregate_measurements, compare_groups, find_missing_edges, find_conflicts, retrieve_evidence, build_subgraph, rank_claims.

Top-1 задачи DB: versioned facts, geo indexes, numeric interval indexes, access-aware filters, graph neighborhood fallback, performance tuning, p50/p95 dashboard, backup/restore, migration scripts.

Definition of Done для DB: базы поднимаются из миграций; индексы созданы; ingestion пишет данные; retrieval читает данные; source_span_id сквозной; performance smoke проходит; данные можно сбросить и загрузить заново.

## 28. Точки синхронизации

Sync 0. Старт. Команда подтверждает цель, роли, официальный список требований, MVP cutoff, структуру репозитория и расписание. Нельзя начинать писать разные контракты вразнобой.

Sync 1. Контракты заморожены. Утверждаются shared DTO: NormalizedDocument, SourceSpan, TableBlock, Claim, QueryIR, EvidenceBundle, AnswerPayload, GraphSubgraph, IngestionReport, UserRole, AccessPolicy, AuditEvent. После этого фронтенд может делать mock UI, backend — endpoints, DB — схемы, ML — structured outputs.

Sync 2. Инфраструктура поднята. SRE показывает, что docker-compose поднимает Gateway, UI, PostgreSQL, Neo4j, Qdrant, MinIO, Redis и healthchecks. Backend показывает /health. Frontend показывает стартовую страницу. DB показывает, что миграции применились.

Sync 3. Ingestion skeleton. Backend и Ingestion принимают файл/ZIP, сохраняют исходник, создают task_id. DB видит task в PostgreSQL. UI показывает статус загрузки. На этом этапе ещё не обязательно извлекать все сущности, но файл должен пройти путь от UI до storage.

Sync 4. NormalizedDocument и SourceSpan. Ingestion возвращает normalized artifacts, таблицы и source spans. ML видит вход для extraction. DB видит documents/source spans. UI может открыть source viewer на mock или real source span.

Sync 5. Граф и векторное хранилище. Knowledge пишет entities, aliases, claims в Neo4j. Retrieval пишет chunks/table rows в Qdrant. DB показывает smoke query по Neo4j и Qdrant. SourceSpan связывает факт и документ.

Sync 6. Первый query end-to-end. Один официальный вопрос проходит от UI до AnswerPayload. Ответ может быть сырой, но должен иметь таблицу, источник, confidence и хотя бы простой граф.

Sync 7. MVP freeze. Все четыре официальных вопроса проходят в базовом виде. Работают upload, ingestion, graph, retrieval, answer, sources, local graph, audit, access role, export Markdown/JSON. Команда запрещает крупные архитектурные изменения.

Sync 8. Top-1 features. Подключаются gap/conflict, review console, dashboards, notifications, PDF/JSON-LD export, manager dashboard, performance trace. Каждая функция подключается только через существующие contracts.

Sync 9. Performance and reliability. SRE, backend и DB запускают perf-smoke, e2e, eval. ML проверяет official gold dataset. Frontend проходит demo script. Все баги фиксируются по приоритету: demo blockers, data correctness, access/security, UI polish.

Sync 10. Submission freeze. Код, deploy, архив, видео, презентация, README, demo script, ссылки и чеклист готовы. После этой точки нельзя добавлять новые функции, можно только исправлять критические баги.

## 29. План по времени

Часы 0–2: старт, роли, contracts, репозиторий, ontology skeleton, official questions, data inventory. Результат: никто не пишет несовместимые DTO.

Часы 2–5: инфраструктура, сервисные каркасы, healthchecks, UI skeleton, OpenAPI skeleton, миграции, Qdrant/Neo4j collections. Результат: make up поднимает систему.

Часы 5–9: upload, storage, parsing, NormalizedDocument, SourceSpan, справочники, table parser basic. Результат: demo files загружаются и превращаются в normalized artifacts.

Часы 9–14: extraction, aliases, quantities, geo/date extraction, claims, Neo4j write, Qdrant upsert. Результат: база знаний содержит первые факты и источники.

Часы 14–18: Query IR, retrieval, fusion, answer synthesis, source links, local graph. Результат: один официальный вопрос проходит end-to-end.

Часы 18–24: MVP hardening. Четыре официальных вопроса, audit, role/access minimal, export Markdown/JSON, e2e tests, reset demo. Результат: MVP freeze.

Часы 24–34: топовые функции: gaps/conflicts, review, dashboards, notifications, advanced source viewer, manager dashboard, performance trace, JSON-LD/PDF. Результат: решение выглядит как продукт.

Часы 34–42: качество: eval, latency, bugfix, UI polish, demo story, official answers, screenshots, README, deploy. Результат: можно записывать видео.

Часы 42–48: стабилизация и сдача. Нельзя начинать новые фичи. Только баги, видео, презентация, ссылки, архив, финальный прогон.

## 30. End-to-end тесты

E2E-1: загрузка ZIP. Пользователь загружает demo corpus, видит task, видит прогресс, видит ingestion report. Проверяется, что исходники сохранены, documents созданы, source spans есть.

E2E-2: таблица. Загружается XLSX/табличный PDF/CSV, система извлекает строки, единицы, числовые значения, source span до ячейки. Ответ содержит значение с ссылкой на строку.

E2E-3: официальный вопрос про обессоливание. Проверяется numeric interval matching, таблица методов, sources, confidence, warnings.

E2E-4: официальный вопрос про католит. Проверяются aliases, оборудование, скорость потока, мировая практика, source spans.

E2E-5: официальный вопрос про Au/Ag/МПГ. Проверяется временной фильтр за последние 5 лет, материалы штейн/шлак, таблица экспериментов.

E2E-6: официальный вопрос про шахтные воды. Проверяется отечественная/зарубежная практика, география, технико-экономические показатели.

E2E-7: доступ. External partner задаёт тот же вопрос, но не видит закрытые источники. Audit log фиксирует access_denied или filtered_sources.

E2E-8: экспорт. Пользователь экспортирует Markdown/JSON, файл содержит evidence и не содержит закрытых источников без прав.

E2E-9: версия факта. Добавляется новый источник, который обновляет или конфликтует со старым claim. Система создаёт новую версию или конфликт.

E2E-10: уведомление. Пользователь указал интересы, добавлен новый документ по теме, появляется уведомление.

## 31. Evaluation

Gold dataset должен включать минимум четыре официальных вопроса и ещё 6–16 дополнительных. Для каждого вопроса нужно зафиксировать expected entities, expected numeric constraints, expected geography, expected source spans, expected answer outline, expected conflicts/gaps, допустимые единицы и tolerance.

Метрики MVP: SourceSpan Citation Coverage, Numeric Correctness, Evidence Recall@k, Unsupported Claim Rate, Entity Linking F1, Retrieval Latency, Answer Completeness.

Метрики топ-1: Geo Correctness, Access Filtering Correctness, Conflict Detection Accuracy, Gap Precision, Export Completeness, p50/p95 latency, query trace completeness.

Evaluation report должен быть виден в UI или доступен как Markdown/JSON. В презентации нужно показать, что команда не просто верит системе, а измеряет её качество.

## 32. Риски и fallback

Риск: парсинг документов ломается. Fallback: text extraction fallback, сохранение raw file, parse warnings, обработка CSV/XLSX как backbone.

Риск: таблицы плохо извлекаются. Fallback: отдельный table parser, простые CSV/XLSX first, ручная проверка demo tables, cell-level provenance только там, где уверены.

Риск: LLM плохо извлекает сущности. Fallback: schema-aware prompts, справочники, rule-based numbers, candidate layer, partial graph.

Риск: алиасы склеиваются неправильно. Fallback: scope для alias, confidence thresholds, candidate merge, review only high-impact.

Риск: Query IR теряет условия. Fallback: presets для официальных типов запросов без хардкода ответов, JSON schema validation, tests на 4 официальных вопросах.

Риск: PCST нестабилен. Fallback: GraphNeighborhood with ranking и timeout.

Риск: 3–5 секунд не выдерживаются. Fallback: precomputed demo corpus, top-k limits, cached embeddings, streaming, retrieval before synthesis, simple answer first.

Риск: внешняя LLM API недоступна. Fallback: mock/cached demo mode, local lightweight model for Query IR, precomputed extraction for demo corpus, clear degraded mode.

Риск: RBAC случайно показывает закрытый источник. Fallback: access filter before retrieval result leaves backend, security e2e test, deny by default.

Риск: deploy ломается. Fallback: локальное видео, заранее записанный demo, Docker instructions, резервный ноутбук, локальный сервер.

Риск: команда начинает слишком много фич. Fallback: MVP freeze rule, запрет новых функций после Sync 10.

## 33. Чеклист MVP

Docker compose поднимает весь стек. UI открывается. Gateway отвечает. Все сервисы имеют healthcheck. PostgreSQL, Neo4j и Qdrant доступны. Можно загрузить ZIP или набор файлов. Создаётся ingestion task. Создаётся NormalizedDocument. Создаются SourceSpan. Таблицы извлекаются базово. Справочники загружены. Сущности извлекаются. Числа и единицы извлекаются. Алиасы находятся хотя бы базово. Claims пишутся в Neo4j. Chunks/table rows пишутся в Qdrant. Query IR строится. Retrieval работает. Fusion работает. Ответ возвращается в чат. Таблица отображается. Source links открываются. Локальный граф строится. Geo filter работает хотя бы базово. Numeric interval работает хотя бы на официальном вопросе. Audit log пишет запросы. Роли работают минимально. Export Markdown/JSON работает. Четыре официальных вопроса отвечаются. Demo script готов.

## 34. Чеклист топ-1

Review console показывает candidates и conflicts. Gap/conflict view работает. Manager dashboard показывает покрытие знаний. Evaluation dashboard показывает метрики. Notification center работает. User interests работают. PDF export работает. JSON-LD export работает. Fact versioning видно в данных или UI. Geo model различает source country, practice country и jurisdiction. Performance trace показывается. p50/p95 latency замерены. PCST или GraphNeighborhood fallback работает. Source viewer подсвечивает фрагмент. Таблицы имеют cell-level provenance. Access-aware retrieval протестирован. Demo deploy доступен. Видео записано. Презентация готова. Архив кода готов. README воспроизводится. Submission links проверены.

## 35. Правила для ИИ-агентов

Каждый агент получает только конкретную задачу, контекст сервиса, входные DTO, выходные DTO, ограничения и Definition of Done. Агент не получает задачу “сделай весь сервис”.

Каждый агент обязан использовать файлы agent_context/common_system.md и свой role-файл. Для задачи по сервису агент также получает README сервиса, shared contracts, API contracts, ontology files и тесты.

Агенту запрещено менять shared contracts, ontology, domain pack, Docker networking, public API, database migrations и security rules без отдельного решения команды.

Агенту можно делегировать boilerplate, тесты, компоненты, DTO, адаптеры, prompts, utility functions, миграции, Dockerfiles, README. Агенту нельзя доверять доменную истинность, финальные answers, aggressive entity merge, численные конверсии без правил, security policy, performance claims.

Результат работы агента считается принятым только после тестов, review человеком и интеграции в общий поток.

## 36. Финальная демо-история

Демо должно начинаться с проблемы: знания разрознены, отчёты, статьи, таблицы и эксперты не связаны, исследователь тратит время на повторный поиск и получает противоречивые выводы.

Дальше показываем загрузку корпуса и справочников. Система показывает ingestion report: документы, таблицы, source spans, сущности, claims, candidates, conflicts.

Затем показываем официальный вопрос про обессоливание. Ответ содержит краткий вывод, таблицу методов, числовые ограничения, источники, confidence и warning по слабым местам.

Затем показываем вопрос про католит или шахтные воды, чтобы продемонстрировать географию и технические решения. Обязательно открыть source span.

Затем показываем локальный граф: материал, процесс, оборудование, результат, источник, эксперт. Граф должен быть компактным.

Затем показываем gap/conflict: система не только отвечает, но и показывает, где знания слабые или противоречивые.

Затем показываем manager dashboard, notification или export как вау-фичу. В конце показываем, что всё это не магия: есть evaluation report, audit log, роли доступа и воспроизводимый docker запуск.

Финальная фраза: “Научный клубок превращает разрозненные документы и таблицы в проверяемую карту знаний, где каждый вывод связан с источником, условиями, числом, географией, экспертом и статусом достоверности”.

## 37. Что нельзя делать

Нельзя делать просто чат по документам. Нельзя выдавать ответы без источников. Нельзя хардкодить ответы на официальные вопросы. Нельзя строить полную OWL-систему, если из-за этого не будет end-to-end. Нельзя начинать OCR и анализ картинок как обязательный путь, если текст и таблицы уже доступны. Нельзя рисовать полный граф на миллион узлов. Нельзя давать LLM свободно выполнять Cypher без Query IR. Нельзя игнорировать географию. Нельзя игнорировать роли и аудит. Нельзя утверждать производительность без trace. Нельзя менять контракты без sync. Нельзя добавлять фичи после freeze.

## 38. Итог

Идеальное решение для топ-1 — это не набор отдельных красивых функций. Это единый продуктовый и инженерный контур: данные загружаются, нормализуются, превращаются в claims с источниками, записываются в граф и поиск, отвечают на сложные вопросы, показывают доказательства, географию, числа, конфликты, пробелы, экспертов, доступ, аудит, экспорт и качество.

Команда выигрывает, если жюри увидит три вещи: решение реально работает end-to-end, решение глубоко попадает в задачу горно-металлургического R&D, решение спроектировано как масштабируемая платформа, а не как одноразовая демонстрация.

Главная дисциплина: сначала MVP, потом максимум. Главный технический закон: ни одного подтверждённого факта без источника. Главный продуктовый закон: исследователь должен видеть не просто ответ, а доказуемую цепочку от вопроса до источника и следующего шага.
