-- PR-003 CRM Supabase — 0001 init. Mirror 1:1 SQLite (apps/crm-core/src/crm/db.py).
-- Idempotent. Không chứa secret.

create table if not exists contacts (
    id          text primary key,
    name        text,
    phone       text,
    email       text,
    source      text,
    tags        text not null default '',
    created_at  timestamptz not null default now()
);

create table if not exists conversations (
    id          text primary key,
    contact_id  text not null references contacts(id) on delete cascade,
    channel     text not null,
    message     text not null,
    timestamp   timestamptz not null default now()
);

create table if not exists pipeline (
    contact_id  text primary key references contacts(id) on delete cascade,
    stage       text not null check (stage in ('lead','contacted','qualified','proposal','won','lost'))
);

create index if not exists idx_conversations_contact on conversations(contact_id);
create index if not exists idx_contacts_phone on contacts(phone);
create index if not exists idx_contacts_email on contacts(email);
