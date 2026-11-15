-- Film Keşfetme ve İnceleme Platformu | Başlangıç şeması v1.2
-- Veritabanı sorumlusu: Muratcan Asarkaya
--
-- v1.2 değişiklikleri (v1.1'e göre):
--   * movies, genres, actors: tmdb_id artık NOT NULL (aynı kayıt iki kez eklenmesin)
--   * reports tablosu eklendi (şikayet gönderme ve moderatör kararı)
--   * pg_trgm eklentisi ve arama/akış için indeksler eklendi
BEGIN;
SET LOCAL search_path TO public;
-- Film adında benzerlik/kısmi eşleşme araması için (ILIKE ve %).
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE TABLE users (
    user_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username VARCHAR(30) NOT NULL,
    email VARCHAR(254) NOT NULL,
    password_hash TEXT NOT NULL,
    display_name VARCHAR(100),
    bio TEXT,
    avatar_url TEXT,
    role VARCHAR(10) NOT NULL DEFAULT 'member',
    account_status VARCHAR(9) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_users_username UNIQUE (username),
    CONSTRAINT uq_users_email UNIQUE (email),
    CONSTRAINT ck_users_username CHECK (username ~ '^[a-z0-9_]{3,30}$'),
    CONSTRAINT ck_users_email_normalized CHECK (
        email = lower(btrim(email))
        AND char_length(email) >= 3
    ),
    CONSTRAINT ck_users_password_hash CHECK (char_length(btrim(password_hash)) > 0),
    CONSTRAINT ck_users_role CHECK (role IN ('member', 'moderator', 'admin')),
    CONSTRAINT ck_users_account_status CHECK (account_status IN ('active', 'suspended'))
);
CREATE TABLE movies (
    movie_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tmdb_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    original_title TEXT,
    overview TEXT,
    release_date DATE,
    runtime_minutes SMALLINT,
    original_language VARCHAR(10),
    poster_path TEXT,
    tmdb_vote_average NUMERIC(5, 3),
    tmdb_vote_count INTEGER,
    tmdb_synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_movies_tmdb_id UNIQUE (tmdb_id),
    CONSTRAINT ck_movies_tmdb_id CHECK (tmdb_id > 0),
    CONSTRAINT ck_movies_title CHECK (char_length(btrim(title)) > 0),
    CONSTRAINT ck_movies_runtime CHECK (runtime_minutes > 0),
    CONSTRAINT ck_movies_tmdb_vote_average CHECK (
        tmdb_vote_average BETWEEN 0 AND 10
    ),
    CONSTRAINT ck_movies_tmdb_vote_count CHECK (tmdb_vote_count >= 0)
);
CREATE TABLE genres (
    genre_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tmdb_id INTEGER NOT NULL,
    name VARCHAR(80) NOT NULL,
    CONSTRAINT uq_genres_tmdb_id UNIQUE (tmdb_id),
    CONSTRAINT uq_genres_name UNIQUE (name),
    CONSTRAINT ck_genres_tmdb_id CHECK (tmdb_id > 0),
    CONSTRAINT ck_genres_name CHECK (char_length(btrim(name)) > 0)
);
-- Bir film birden çok türe, bir tür birden çok filme bağlanabilir.
CREATE TABLE movie_genres (
    movie_id BIGINT NOT NULL,
    genre_id BIGINT NOT NULL,
    CONSTRAINT pk_movie_genres PRIMARY KEY (movie_id, genre_id),
    CONSTRAINT fk_movie_genres_movie FOREIGN KEY (movie_id) REFERENCES movies (movie_id) ON DELETE CASCADE,
    CONSTRAINT fk_movie_genres_genre FOREIGN KEY (genre_id) REFERENCES genres (genre_id) ON DELETE CASCADE
);
CREATE TABLE actors (
    actor_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tmdb_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    profile_path TEXT,
    CONSTRAINT uq_actors_tmdb_id UNIQUE (tmdb_id),
    CONSTRAINT ck_actors_tmdb_id CHECK (tmdb_id > 0),
    CONSTRAINT ck_actors_name CHECK (char_length(btrim(name)) > 0)
);
-- Oyuncunun bir filmdeki rolü/jenerik kaydı. Aynı kişi aynı filmde
-- birden çok rolde bulunabilir; oyuncu adı bir benzersiz anahtar değildir.
CREATE TABLE movie_cast (
    cast_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    movie_id BIGINT NOT NULL,
    actor_id BIGINT NOT NULL,
    tmdb_credit_id TEXT,
    character_name TEXT,
    cast_order INTEGER,
    CONSTRAINT uq_movie_cast_tmdb_credit UNIQUE (tmdb_credit_id),
    CONSTRAINT fk_movie_cast_movie FOREIGN KEY (movie_id) REFERENCES movies (movie_id) ON DELETE CASCADE,
    CONSTRAINT fk_movie_cast_actor FOREIGN KEY (actor_id) REFERENCES actors (actor_id) ON DELETE CASCADE,
    CONSTRAINT ck_movie_cast_tmdb_credit CHECK (
        tmdb_credit_id IS NULL
        OR char_length(btrim(tmdb_credit_id)) > 0
    ),
    CONSTRAINT ck_movie_cast_order CHECK (cast_order >= 0)
);
-- Kullanıcı başına film başına tek güncel puan; 1-10 arasında tam sayı.
CREATE TABLE ratings (
    user_id BIGINT NOT NULL,
    movie_id BIGINT NOT NULL,
    score SMALLINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_ratings PRIMARY KEY (user_id, movie_id),
    CONSTRAINT fk_ratings_user FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
    CONSTRAINT fk_ratings_movie FOREIGN KEY (movie_id) REFERENCES movies (movie_id) ON DELETE CASCADE,
    CONSTRAINT ck_ratings_score CHECK (
        score BETWEEN 1 AND 10
    )
);
-- İnceleme ve puan birbirinden bağımsızdır; biri olmadan diğeri eklenebilir.
CREATE TABLE reviews (
    review_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL,
    movie_id BIGINT NOT NULL,
    body TEXT NOT NULL,
    contains_spoiler BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(9) NOT NULL DEFAULT 'published',
    moderated_by BIGINT,
    moderated_at TIMESTAMPTZ,
    moderation_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_reviews_user_movie UNIQUE (user_id, movie_id),
    CONSTRAINT fk_reviews_user FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
    CONSTRAINT fk_reviews_movie FOREIGN KEY (movie_id) REFERENCES movies (movie_id) ON DELETE CASCADE,
    CONSTRAINT fk_reviews_moderated_by FOREIGN KEY (moderated_by) REFERENCES users (user_id) ON DELETE
    SET NULL,
        CONSTRAINT ck_reviews_body CHECK (
            body ~ '[^[:space:]]'
            AND char_length(body) <= 10000
        ),
        CONSTRAINT ck_reviews_status CHECK (status IN ('published', 'hidden'))
);
-- İzlenecekler: kullanıcıya ait tek varsayılan liste; üyelik çiftle temsil edilir.
CREATE TABLE watchlist (
    user_id BIGINT NOT NULL,
    movie_id BIGINT NOT NULL,
    added_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_watchlist PRIMARY KEY (user_id, movie_id),
    CONSTRAINT fk_watchlist_user FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
    CONSTRAINT fk_watchlist_movie FOREIGN KEY (movie_id) REFERENCES movies (movie_id) ON DELETE CASCADE
);
-- "Özel liste" = kullanıcının adlandırdığı liste. Görünürlük ayrıca belirlenir.
CREATE TABLE user_lists (
    list_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    visibility VARCHAR(7) NOT NULL DEFAULT 'private',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_user_lists_user FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
    CONSTRAINT ck_user_lists_name CHECK (char_length(btrim(name)) > 0),
    CONSTRAINT ck_user_lists_visibility CHECK (visibility IN ('public', 'private'))
);
CREATE TABLE list_items (
    list_id BIGINT NOT NULL,
    movie_id BIGINT NOT NULL,
    added_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_list_items PRIMARY KEY (list_id, movie_id),
    CONSTRAINT fk_list_items_list FOREIGN KEY (list_id) REFERENCES user_lists (list_id) ON DELETE CASCADE,
    CONSTRAINT fk_list_items_movie FOREIGN KEY (movie_id) REFERENCES movies (movie_id) ON DELETE CASCADE
);
-- Yönlü ilişki: A'nın B'yi takip etmesi, B'nin de A'yı takip ettiği anlamına gelmez.
CREATE TABLE follows (
    follower_id BIGINT NOT NULL,
    followed_id BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_follows PRIMARY KEY (follower_id, followed_id),
    CONSTRAINT fk_follows_follower FOREIGN KEY (follower_id) REFERENCES users (user_id) ON DELETE CASCADE,
    CONSTRAINT fk_follows_followed FOREIGN KEY (followed_id) REFERENCES users (user_id) ON DELETE CASCADE,
    CONSTRAINT ck_follows_no_self_follow CHECK (follower_id <> followed_id)
);
-- Şikayet: bir incelemeye YA DA bir listeye yönelir (ikisinden tam biri dolu).
-- status: open -> resolved (işlem yapıldı) veya dismissed (reddedildi).
CREATE TABLE reports (
    report_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    reporter_id BIGINT NOT NULL,
    review_id BIGINT,
    list_id BIGINT,
    reason VARCHAR(10) NOT NULL,
    details TEXT,
    status VARCHAR(9) NOT NULL DEFAULT 'open',
    resolved_by BIGINT,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_reports_reporter FOREIGN KEY (reporter_id) REFERENCES users (user_id) ON DELETE CASCADE,
    CONSTRAINT fk_reports_review FOREIGN KEY (review_id) REFERENCES reviews (review_id) ON DELETE CASCADE,
    CONSTRAINT fk_reports_list FOREIGN KEY (list_id) REFERENCES user_lists (list_id) ON DELETE CASCADE,
    CONSTRAINT fk_reports_resolved_by FOREIGN KEY (resolved_by) REFERENCES users (user_id) ON DELETE
    SET NULL,
        CONSTRAINT ck_reports_one_target CHECK (num_nonnulls(review_id, list_id) = 1),
        CONSTRAINT ck_reports_reason CHECK (reason IN ('spam', 'abuse', 'spoiler', 'other')),
        CONSTRAINT ck_reports_status CHECK (status IN ('open', 'resolved', 'dismissed')),
        CONSTRAINT ck_reports_resolution CHECK (
            (
                status = 'open'
                AND resolved_at IS NULL
            )
            OR (
                status <> 'open'
                AND resolved_at IS NOT NULL
            )
        )
);
-- Aynı kullanıcı aynı içeriği açık durumdayken ikinci kez şikayet edemez.
CREATE UNIQUE INDEX uq_reports_open_review ON reports (reporter_id, review_id)
WHERE status = 'open'
    AND review_id IS NOT NULL;
CREATE UNIQUE INDEX uq_reports_open_list ON reports (reporter_id, list_id)
WHERE status = 'open'
    AND list_id IS NOT NULL;
-- İndeksler. Birincil anahtar ve UNIQUE kısıtları zaten kendi indeksini oluşturur.
CREATE INDEX idx_movies_title_trgm ON movies USING gin (title gin_trgm_ops);
CREATE INDEX idx_movies_release_date ON movies (release_date);
CREATE INDEX idx_ratings_movie ON ratings (movie_id);
CREATE INDEX idx_ratings_user_created ON ratings (user_id, created_at DESC);
CREATE INDEX idx_reviews_movie_created ON reviews (movie_id, created_at DESC);
CREATE INDEX idx_reviews_user_created ON reviews (user_id, created_at DESC);
CREATE INDEX idx_follows_followed ON follows (followed_id);
CREATE INDEX idx_user_lists_user ON user_lists (user_id);
CREATE INDEX idx_list_items_movie ON list_items (movie_id);
CREATE INDEX idx_watchlist_movie ON watchlist (movie_id);
CREATE INDEX idx_movie_cast_movie ON movie_cast (movie_id, cast_order);
CREATE INDEX idx_movie_cast_actor ON movie_cast (actor_id);
CREATE INDEX idx_movie_genres_genre ON movie_genres (genre_id);
CREATE INDEX idx_reports_status_created ON reports (status, created_at);
-- updated_at alanı, bu beş tablodaki UPDATE işlemlerinde otomatik yenilenir.
CREATE FUNCTION set_updated_at() RETURNS TRIGGER LANGUAGE plpgsql AS $$ BEGIN NEW.updated_at := CURRENT_TIMESTAMP;
RETURN NEW;
END;
$$;
CREATE TRIGGER trg_users_updated_at BEFORE
UPDATE ON users FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_movies_updated_at BEFORE
UPDATE ON movies FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_ratings_updated_at BEFORE
UPDATE ON ratings FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_reviews_updated_at BEFORE
UPDATE ON reviews FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_user_lists_updated_at BEFORE
UPDATE ON user_lists FOR EACH ROW EXECUTE FUNCTION set_updated_at();
-- Platform ortalaması yalnızca yerel ratings kayıtlarından hesaplanır.
-- Puan yoksa average_score NULL, rating_count 0'dır. TMDB puanı karışmaz.
CREATE VIEW movie_rating_stats AS
SELECT m.movie_id,
    count(r.user_id) AS rating_count,
    round(avg(r.score), 2) AS average_score
FROM movies AS m
    LEFT JOIN ratings AS r ON r.movie_id = m.movie_id
GROUP BY m.movie_id;
-- Akış için mantıksal görünüm: ayrıca bir activity tablosuna INSERT yapılmaz.
-- Özel listeler ve watchlist bu ortak aktivite görünümünde yer almaz.
-- Her kayıt kaynak satırın güncel durumunu ve ilk oluşturulma zamanını gösterir.
-- Düzenleme geçmişi / kalıcı olay günlüğü değildir.
CREATE VIEW activity_events (
    event_id,
    actor_id,
    event_type,
    movie_id,
    review_id,
    list_id,
    target_user_id,
    score,
    occurred_at
) AS
SELECT 'rating:' || r.user_id::TEXT || ':' || r.movie_id::TEXT,
    r.user_id,
    'movie_rated'::TEXT,
    r.movie_id,
    NULL::BIGINT,
    NULL::BIGINT,
    NULL::BIGINT,
    r.score,
    r.created_at
FROM ratings AS r
UNION ALL
SELECT 'review:' || r.review_id::TEXT,
    r.user_id,
    'review_written'::TEXT,
    r.movie_id,
    r.review_id,
    NULL::BIGINT,
    NULL::BIGINT,
    NULL::SMALLINT,
    r.created_at
FROM reviews AS r
WHERE r.status = 'published'
UNION ALL
SELECT 'list:' || l.list_id::TEXT,
    l.user_id,
    'list_created'::TEXT,
    NULL::BIGINT,
    NULL::BIGINT,
    l.list_id,
    NULL::BIGINT,
    NULL::SMALLINT,
    l.created_at
FROM user_lists AS l
WHERE l.visibility = 'public'
UNION ALL
SELECT 'list_item:' || i.list_id::TEXT || ':' || i.movie_id::TEXT,
    l.user_id,
    'movie_added_to_list'::TEXT,
    i.movie_id,
    NULL::BIGINT,
    l.list_id,
    NULL::BIGINT,
    NULL::SMALLINT,
    i.added_at
FROM list_items AS i
    JOIN user_lists AS l ON l.list_id = i.list_id
WHERE l.visibility = 'public'
UNION ALL
SELECT 'follow:' || f.follower_id::TEXT || ':' || f.followed_id::TEXT,
    f.follower_id,
    'user_followed'::TEXT,
    NULL::BIGINT,
    NULL::BIGINT,
    NULL::BIGINT,
    f.followed_id,
    NULL::SMALLINT,
    f.created_at
FROM follows AS f;
COMMIT;