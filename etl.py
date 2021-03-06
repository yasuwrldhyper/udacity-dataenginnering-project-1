import io
import os
import glob
import psycopg2
import pandas as pd
from sql_queries import *


def process_song_file(cur, filepath):
    """Process a Song File

    Extract Data for Songs Table, Artists Table and
    insert Record into Song Table, Artists Table

    Args:
        cur (cursor): posgres cursor
        filepath (string): song dataset filepath
    """
    # open song file
    df = pd.read_json(filepath, lines=True)
    # convert NaN to zero
    df.fillna(0, inplace=True)

    # For Debug
    # print(df.head())

    # insert song record
    song_data = df[['song_id',
                    'title',
                    'artist_id',
                    'year',
                    'duration']].values.tolist()[0]

    # print('insert song record')
    cur.execute(song_table_insert, song_data)

    # insert artist record
    artist_data = df[['artist_id', 'artist_name',
                      'artist_location', 'artist_latitude',
                      'artist_longitude'
                      ]].values.tolist()[0]
    # print('insert artist record')
    cur.execute(artist_table_insert, artist_data)


def process_log_file(cur, filepath):
    """Process a Log File

    Extract Data for time, users, songplays Table and
    insert Record into time , users, songplays Table

    Args:
        cur (cursor): posgres cursor
        filepath (string): log dataset filepath
    """

    # open log file
    df = pd.read_json(filepath, lines=True)

    # filter by NextSong action
    df = df[df["page"].str.contains("NextSong")]

    # convert timestamp column to datetime
    t = pd.to_datetime(df["ts"], origin="unix", unit="ms")

    # insert time data records
    time_data = (t, t.dt.hour, t.dt.day, t.dt.isocalendar().week,
                 t.dt.month, t.dt.year, t.dt.weekday)
    column_labels = ("ts", "hour", "day", "week", "month", "year", "weekday")
    time_df = pd.DataFrame(dict(zip(column_labels, time_data)))

    for i, row in time_df.iterrows():
        cur.execute(time_table_insert, list(row))

    # load user table
    user_df = df[["userId", "firstName", "lastName", "gender", "level"]]

    # insert user records
    for i, row in user_df.iterrows():
        cur.execute(user_table_insert, row)

    songplay_csv = io.StringIO()

    # insert songplay records
    for index, row in df.iterrows():

        # get songid and artistid from song and artist tables
        cur.execute(song_select, (row.song, row.artist, row.length))
        results = cur.fetchone()

        if results:
            songid, artistid = results
        else:
            songid, artistid = 'None', 'None'

        # insert songplay record
        t = pd.to_datetime(row.ts, origin="unix", unit="ms")

        songplay_data = (t.isoformat(), str(row.userId), row.level, songid,
                         artistid, str(row.sessionId), str(row.location), row.userAgent)

        # convert csv data.
        songplay_csv.write('|'.join(songplay_data) + '\n')

    # COPY songplays record.
    songplay_csv.seek(0)
    cur.copy_from(
        songplay_csv,
        'songplays',
        sep='|',
        null='None',
        columns=('start_time',
                 'user_id',
                 'level',
                 'song_id',
                 'artist_id',
                 'session_id',
                 'location',
                 'user_agent')
    )


def process_data(cur, conn, filepath, func):
    """Process Data

    Execute ETL processing of data sets classified by type.

    Args:
        cur (cursor): posgres cursor
        conn (connection): posgres connection
        filepath (string): top directory for dataset
        func (function): process function for each files
    """

    # get all files matching extension from directory
    all_files = []
    for root, dirs, files in os.walk(filepath):
        files = glob.glob(os.path.join(root, '*.json'))
        for f in files:
            all_files.append(os.path.abspath(f))

    # get total number of files found
    num_files = len(all_files)
    print('{} files found in {}'.format(num_files, filepath))

    # iterate over files and process
    for i, datafile in enumerate(all_files, 1):
        # print('file {} processing'.firmat(datafile))
        func(cur, datafile)
        conn.commit()
        print('{}/{} files processed.'.format(i, num_files))


def main():
    """main function

    """

    conn = psycopg2.connect(
        'host=127.0.0.1 dbname=sparkifydb user=student password=student')
    cur = conn.cursor()

    try:
        process_data(cur, conn, filepath='data/song_data',
                     func=process_song_file)
        process_data(cur, conn, filepath='data/log_data',
                     func=process_log_file)
    except psycopg2.Error as e:
        print("Error: Issue process data")
        print(e)
        print('PgError Code' + e.pgcode)
    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    main()
