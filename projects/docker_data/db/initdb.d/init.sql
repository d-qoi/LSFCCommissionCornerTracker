-- Databases:
CREATE DATABASE cctracker;
CREATE DATABASE keycloak WITH ENCODING 'UTF8';

-- Users
CREATE USER webserver_user WITH ENCRYPTED PASSWORD 'cctracker_pass';
CREATE USER ptbapp_user WITH ENCRYPTED PASSWORD 'ptbapp_pass';
CREATE USER keycloak_user WITH ENCRYPTED PASSWORD 'keycloakpass';

-- grants
GRANT ALL PRIVILEGES ON DATABASE keycloak TO keycloak_user;
GRANT ALL PRIVILEGES ON DATABASE cctracker TO webserver_user;
GRANT ALL PRIVILEGES ON DATABASE cctracker TO ptbapp_user;


-- fixing keycloak public complaints
REVOKE CONNECT ON DATABASE keycloak FROM PUBLIC;
GRANT CONNECT ON DATABASE keycloak TO keycloak_user;

\connect keycloak;
REVOKE ALL ON SCHEMA public FROM PUBLIC;

ALTER SCHEMA public OWNER TO keycloak_user;
GRANT USAGE, CREATE ON SCHEMA public TO keycloak_user;

\connect cctracker;
GRANT ALL ON SCHEMA public TO webserver_user;
GRANT ALL ON SCHEMA public TO ptbapp_user;