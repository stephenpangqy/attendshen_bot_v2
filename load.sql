drop database if exists attendshen;
create database attendshen;
use attendshen;

create table users (
	chat_id int not null primary key,
    name varchar(255) not null
);

create table user_sections (
    chat_id int not null,
    section varchar(100) not null,
    role varchar(100) not null, # Admin or Student

    constraint primary key (chat_id,section)
);


create table events (
    event_id int primary key auto_increment,
    event_name varchar(100) not null,
	section varchar(100) not null,
    code_word varchar(20) not null,
    completed char(1) not null # 0 for ongoing, 1 for complete
);

create table attendance (
	# Contains attendance of students for each event
    event_id int not null,
    chat_id int not null,
    mark_time datetime not null,

    constraint primary key (event_id, chat_id)
);

create table late_attendance (
    event_id int not null,
    chat_id int not null,
    status varchar(100) not null, # Valid Reason OR Absent
    reason varchar(100),

    constraint primary key (event_id, chat_id)
);

create table sections (
	section_id varchar(100) primary key,
    section_count int not null # only counting students
    
);

INSERT into sections VALUES ('wad2-g1',0);
INSERT into sections VALUES ('wad2-g2',0);
INSERT into sections VALUES ('wad2-g3',0);
INSERT into sections VALUES ('wad2-g4',0);
INSERT into sections VALUES ('wad2-g5',0);
INSERT into sections VALUES ('wad2-g6',0);
INSERT into sections VALUES ('wad2-g7',0);
INSERT into sections VALUES ('wad2-g8',0);
INSERT into sections VALUES ('wad2-g9',0);
INSERT into sections VALUES ('spm-g1',0);
INSERT into sections VALUES ('spm-g2',0);
INSERT into sections VALUES ('spm-g3',0);
INSERT into sections VALUES ('spm-g4',0);
INSERT into sections VALUES ('spm-g5',0);

INSERT INTO users VALUES (1,'Sarah');
INSERT INTO users VALUES (2,'Geraldine');
INSERT INTO users VALUES (3,'Lucy');
INSERT INTO users VALUES (4,'Kariana');
INSERT INTO users VALUES (5,'Shayna');
INSERT INTO users VALUES (6,'Amanda');
INSERT INTO users VALUES (148790980,'Stephen');


INSERT INTO user_sections VALUES (1,'wad2-g2','Student');
INSERT INTO user_sections VALUES (2,'wad2-g2','Student');
INSERT INTO user_sections VALUES (3,'wad2-g2','Student');
INSERT INTO user_sections VALUES (4,'wad2-g2','Student');
INSERT INTO user_sections VALUES (5,'wad2-g2','Student');
INSERT INTO user_sections VALUES (6,'wad2-g2','Student');
INSERT INTO user_sections VALUES (148790980,'wad2-g2','Admin');

INSERT INTO events(event_name,section,code_word,completed) VALUES ('Test 1', 'wad2-g2','test1','0');
INSERT INTO events(event_name,section,code_word,completed) VALUES ('Test 2', 'wad2-g2','test2','0');
INSERT INTO events(event_name,section,code_word,completed) VALUES ('Test 1.2', 'wad2-g1','test1','0');

INSERT INTO attendance VALUES (1,1,0);
INSERT INTO attendance VALUES (1,2,0);
INSERT INTO attendance VALUES (1,3,0);
INSERT INTO attendance VALUES (2,1,0);

INSERT INTO late_attendance VALUES(1,5,'VR','Sick');
INSERT INTO late_attendance VALUES(1,6,'VR','Sick');
INSERT INTO late_attendance VALUES(2,2,'VR','Sick');