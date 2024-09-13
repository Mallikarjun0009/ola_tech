#v1.1 20140528

CREATE TABLE IF NOT EXISTS device_cm_config (
        id smallint(4) AUTO_INCREMENT,
        host_id int(10) NOT NULL,
        device_type_group_id smallint(4) NOT NULL,
        device_user_group_id smallint(4),
        user_name varchar(100),
        login_pass varchar(100),
        enable_pass varchar(100),
        description varchar(500),
        connection_proto varchar(20),
        connection_proto_args varchar(20),
        cm_server_id varchar(20),
        save_config_changes smallint(1) DEFAULT 0,
        last_backup_date datetime,
        last_backup_status smallint(2) DEFAULT '-1',
        last_backup_log varchar(40),
        client_id smallint(4) NOT NULL,
        PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS device_jobs (
        id smallint(4) AUTO_INCREMENT,
        host_id int(10) NOT NULL,
        job_name varchar(50),
        job_group_id smallint(4),
        job_descr varchar(500),
        job_type_id smallint(3),
        last_execution_date datetime,
        last_execution_status smallint(2) DEFAULT '-1',
        last_execution_log varchar(40),
        client_id smallint(4) NOT NULL,
        PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS device_job_types (
        id smallint(3),
        type varchar(50),
        PRIMARY KEY (id)
);

INSERT INTO device_job_types (id,type) VALUES (1,'configuration backup');
INSERT INTO device_job_types (id,type) VALUES (2,'fetch command output');
INSERT INTO device_job_types (id,type) VALUES (3,'task');


CREATE TABLE IF NOT EXISTS device_type_groups (
        id smallint(4),
        name varchar(100) NOT NULL,
        manufacturer varchar(50) NOT NULL,
        models varchar(1000) NOT NULL,
        description varchar(500),
        user_prompt varchar(30),
        enable_prompt varchar(30),
        client_id smallint(4) NOT NULL,
        PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS device_user_groups (
        id smallint(4) AUTO_INCREMENT,
        name varchar(100) NOT NULL,
        user_name varchar(100) NOT NULL,
        login_pass varchar(100) NOT NULL,
        enable_pass varchar(100) NOT NULL,
        description varchar(500),
        client_id smallint(4) NOT NULL,
        PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS cm_server (
        id smallint(4) AUTO_INCREMENT,
        name varchar(100) NOT NULL,
        ip varchar(40) NOT NULL,
        server_root varchar(1000) NOT NULL,
        cm_server_type varchar(500),
        cm_server_description varchar(500),
	cm_server_username varchar(100),
	cm_server_password varchar(100),
        client_id smallint(4) NOT NULL,
        PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS device_job_groups (
        id smallint(4) AUTO_INCREMENT,
        name varchar(100) NOT NULL,
        description varchar(500),
        client_id smallint(4) NOT NULL,
        PRIMARY KEY (id)
);

INSERT INTO device_job_groups (name,client_id) VALUES (1,1);
INSERT INTO device_job_groups (name,client_id) VALUES (2,1);
INSERT INTO device_job_groups (name,client_id) VALUES (3,1);
INSERT INTO device_job_groups (name,client_id) VALUES (4,1);
INSERT INTO device_job_groups (name,client_id) VALUES (5,1);
INSERT INTO device_job_groups (name,client_id) VALUES (6,1);
INSERT INTO device_job_groups (name,client_id) VALUES (7,1);
INSERT INTO device_job_groups (name,client_id) VALUES (8,1);
INSERT INTO device_job_groups (name,client_id) VALUES (9,1);
INSERT INTO device_job_groups (name,client_id) VALUES (10,1);


ALTER TABLE global_config ADD configuration_management_enabled varchar(3);
ALTER TABLE global_config ADD cm_backup_dir varchar(500);
ALTER TABLE global_config ADD cm_licence_key varchar(500);
ALTER TABLE global_config ADD cm_log_dir varchar(500);
ALTER TABLE global_config ADD cm_xml_dir varchar(500);
UPDATE global_config set configuration_management_enabled='no';
UPDATE global_config set cm_backup_dir='/usr/share/gestioip/conf';
UPDATE global_config set cm_log_dir='/usr/share/gestioip/var/log';
UPDATE global_config set cm_xml_dir='/usr/share/gestioip/var/devices';


INSERT IGNORE INTO event_types (id,event_type) VALUES (100,'ping status changed');
INSERT INTO event_types (id,event_type) VALUES (101,'device user group added');
INSERT INTO event_types (id,event_type) VALUES (102,'device user group edited');
INSERT INTO event_types (id,event_type) VALUES (103,'device user group deleted');
INSERT INTO event_types (id,event_type) VALUES (104,'device type group added');
INSERT INTO event_types (id,event_type) VALUES (105,'device type group edited');
INSERT INTO event_types (id,event_type) VALUES (106,'device type group deleted');
INSERT INTO event_types (id,event_type) VALUES (107,'device conf mgnt edited');
INSERT INTO event_types (id,event_type) VALUES (108,'fetch_config executed');
INSERT INTO event_types (id,event_type) VALUES (110,'cm server added');
INSERT INTO event_types (id,event_type) VALUES (111,'cm server edited');
INSERT INTO event_types (id,event_type) VALUES (112,'cm server deleted');
INSERT INTO event_types (id,event_type) VALUES (113,'job group added');
INSERT INTO event_types (id,event_type) VALUES (114,'job group edited');
INSERT INTO event_types (id,event_type) VALUES (115,'job group deleted');


INSERT INTO event_classes (id,event_class) VALUES (20,'conf mgnt');

INSERT INTO predef_host_columns (id,name) VALUES (16,'CM');

