-- Aquest usuari s'encarrega de crear tota l'estructura SQL de l'aplicació a la base de dades triada.
-- En el meu cas, per a executar-lo a MariaDB he emprat la següent comanda: mysql < tu.sql

-- Després de que la base de dades crei l'estructura de dades necessària, faltaria crear un usuari:
-- CREATE USER 'api'@'%' IDENTIFIED BY 'password';
-- GRANT ALL PRIVILEGES ON `targeta_unica`.* TO 'api'@'%';
-- FLUSH PRIVILEGES;

CREATE DATABASE IF NOT EXISTS `targeta_unica`
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE `targeta_unica`;

SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS `passatger` (
    `id`               INT(8)          NOT NULL AUTO_INCREMENT,
    `nom`              VARCHAR(32)     NOT NULL,
    `llinatge_1`       VARCHAR(32)     NOT NULL,
    `llinatge_2`       VARCHAR(32)         NULL,
    `document`         VARCHAR(16)     NOT NULL,
    `email`            VARCHAR(128)    NOT NULL,
    `sessio_iniciada`  BOOLEAN         NOT NULL DEFAULT FALSE,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `2fa` (
    `id`              INT(8)          NOT NULL AUTO_INCREMENT,
    `id_passatger`    INT(8)          NOT NULL,
    `codi`            NUMERIC(8, 0)   NOT NULL,
    `data_creacio`    DATETIME        NOT NULL,
    `data_expiracio`  DATETIME        NOT NULL,
    PRIMARY KEY (`id`),
    CONSTRAINT `fk_2fa_passatger`
        FOREIGN KEY (`id_passatger`)
        REFERENCES `passatger` (`id`)
        ON UPDATE CASCADE
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `targeta` (
    `id`           INT(8)                                                              NOT NULL AUTO_INCREMENT,
    `id_passatger` INT(8)                                                              NOT NULL,
    `codi_targeta` VARCHAR(16)                                                         NOT NULL,
    `perfil`       ENUM('Infantil', 'Jove', 'General', 'Pensionista', 'Altres')        NOT NULL,
    `saldo`        NUMERIC(8, 2)                                                       NOT NULL DEFAULT 0.00,
    `estat`        ENUM('Activa', 'Robada', 'Caducada', 'Perduda', 'Desactivada', 'Altres') NOT NULL DEFAULT 'Activa',
    PRIMARY KEY (`id`),
    CONSTRAINT `fk_targeta_passatger`
        FOREIGN KEY (`id_passatger`)
        REFERENCES `passatger` (`id`)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `targeta_virtual` (
    `id`               INT(16)         NOT NULL AUTO_INCREMENT,
    `id_targeta_mare`  INT(8)          NOT NULL,
    `qr`               VARCHAR(255)    NOT NULL,
    `data_creacio`     DATETIME        NOT NULL,
    `data_expiracio`   DATETIME        NOT NULL,
    PRIMARY KEY (`id`),
    CONSTRAINT `fk_targeta_virtual_targeta`
        FOREIGN KEY (`id_targeta_mare`)
        REFERENCES `targeta` (`id`)
        ON UPDATE CASCADE
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `user` (
    `id`          INT(8)       NOT NULL AUTO_INCREMENT,
    `nom`         VARCHAR(32)  NOT NULL,
    `llinatge_1`  VARCHAR(32)  NOT NULL,
    `llinatge_2`  VARCHAR(32)      NULL,
    `email`       VARCHAR(128) NOT NULL,
    `contrasenya` VARCHAR(128) NOT NULL,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
