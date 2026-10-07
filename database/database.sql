CREATE TABLE sample_entity_status(
    id		                        SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(enumerator)
);

INSERT INTO sample_entity_status (enumerator) VALUES
('created'),
('pending'),
('success'),
('failed');

CREATE TABLE sample_entity(
    id                              SERIAL PRIMARY KEY,
    sample_entity_key               CHAR(36) NOT NULL,
    status_id                       INTEGER NOT NULL REFERENCES sample_entity_status(id),
    sample_entity_data              JSONB NOT NULL,
    name                            VARCHAR(255) NOT NULL,
    email                           VARCHAR(255) NOT NULL,
    document_number                 CHAR(14) NOT NULL,
    birthdate                       DATE NOT NULL,
    counter                         INTEGER NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(sample_entity_key),
    UNIQUE(document_number),
    UNIQUE(email)
);

CREATE TABLE sample_entity_status_event(
    id                              SERIAL PRIMARY KEY,
    sample_entity_id                INTEGER NOT NULL REFERENCES sample_entity(id),
    status_id                       INTEGER NOT NULL REFERENCES sample_entity_status(id),
    event_datetime                  TIMESTAMP NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);


CREATE TABLE client(
    id                  SERIAL PRIMARY KEY,
    client_key          UUID NOT NULL,
    name                VARCHAR(255) NOT NULL,
    document_number     CHAR(11) NOT NULL,
    birth_date          DATE NOT NULL,
    created_at          TIMESTAMP NOT NULL DEFAULT(NOW()),

    UNIQUE(client_key),
    UNIQUE(document_number)
);


CREATE TABLE account_status(
    id                  SERIAL PRIMARY KEY,
    enumerator          VARCHAR(50) NOT NULL,
    created_at          TIMESTAMP NOT NULL DEFAULT(NOW()),

    UNIQUE(enumerator)
);

INSERT INTO account_status (enumerator) VALUES
('active'),
('blocked'),
('closed');



CREATE TABLE account(
    id                  SERIAL PRIMARY KEY,
    account_key         UUID NOT NULL,
    client_id           INTEGER NOT NULL REFERENCES client(id),
    status_id           INTEGER NOT NULL REFERENCES account_status(id),
    balance             NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
    created_at          TIMESTAMP NOT NULL DEFAULT(NOW()),

    UNIQUE(account_key),
    UNIQUE(client_id),

    CHECK(balance >= 0)
);



CREATE TABLE transaction_type(
    id                  SERIAL PRIMARY KEY,
    enumerator          VARCHAR(50) NOT NULL,
    created_at          TIMESTAMP NOT NULL DEFAULT(NOW()),

    UNIQUE(enumerator)
);

INSERT INTO transaction_type (enumerator) VALUES
('deposit'),
('transfer');



CREATE TABLE financial_transaction(
    id                      SERIAL PRIMARY KEY,
    transaction_key         UUID NOT NULL,
    idempotency_key         UUID NOT NULL,

    transaction_type_id     INTEGER NOT NULL REFERENCES transaction_type(id),

    source_account_id       INTEGER REFERENCES account(id),
    destination_account_id  INTEGER NOT NULL REFERENCES account(id),

    amount                  NUMERIC(15, 2) NOT NULL,
    created_at              TIMESTAMP NOT NULL DEFAULT(NOW()),

    UNIQUE(transaction_key),
    UNIQUE(idempotency_key),

    CHECK(amount > 0),

    CHECK(
        source_account_id IS NULL
        OR source_account_id <> destination_account_id
    )
);