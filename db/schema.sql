create table deals (
  id                uuid    primary key default gen_random_uuid(),
  dedup_key         text    not null,
  source            text    not null,
  title             text    not null,
  description       text,
  entry_url         text,
  type              text    not null check (type in ('giveaway','deal','coupon','contest')),
  value_score       int     not null check (value_score between 1 and 10),
  value_description text,
  expiry_date       text,
  found_at          timestamptz default now(),
  entered           boolean default false,
  entered_at        timestamptz,
  entry_email       text,
  entry_attempts    int     default 0,
  flagged_manual    boolean default false,
  won               boolean default false,
  won_at            timestamptz,
  constraint deals_dedup_key_unique unique (dedup_key)
);

create table win_notifications (
  id                uuid    primary key default gen_random_uuid(),
  gmail_message_id  text    not null,
  inbox_email       text    not null,
  subject           text,
  sender            text,
  received_at       timestamptz,
  forwarded_at      timestamptz,
  raw_snippet       text,
  constraint win_notifications_message_id_unique unique (gmail_message_id)
);

create table heartbeat (
  id         text primary key default 'singleton',
  checked_at timestamptz default now()
);

create table app_state (
  key   text primary key,
  value text
);
insert into app_state (key, value) values ('last_digest_sent_at', now()::text);
