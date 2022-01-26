#!/usr/bin/python3

import argparse
import ast
import copy
import pandas as pd
import pyarrow as pa





def read_dfs(waveform_order, dbdir):
    hdf = pd.read_csv('%s/resample_ssf.%s.xz' % (dbdir, waveform_order), dtype=pd.Int64Dtype(), nrows=1)
    match_cols = hdf.columns.to_list()
    match_cols = [col for col in match_cols if col == 'test1_0' or not col.startswith(('vol', 'atk', 'sus', 'rel', 'flt', 'test'))]
    # match_cols = [col for col in match_cols if not col.startswith('freq1') or not col[-1].isdigit()]
    df = pd.read_csv('%s/resample_ssf.%s.xz' % (dbdir, waveform_order), engine='pyarrow', dtype=pd.Int64Dtype(), usecols=match_cols).fillna(0)
    match_cols.remove('hashid')
    match_cols.remove('hashid_noclock')
    return (df, match_cols)


def fuzzy_match(hashid, df, match_cols):
    matching_hashids = {hashid}
    i = 0
    while i != len(matching_hashids):
        i = len(matching_hashids)
        hashid_df = df[df.hashid.isin(matching_hashids)]
        match_df = pd.merge(df, hashid_df, on=match_cols).set_index('hashid_x')
        noclocks = set(match_df.hashid_noclock_x.unique())
        matching_hashids.update(set(match_df.index.unique()))
        matching_hashids.update(set(df[df.hashid_noclock.isin(noclocks)].hashid.unique()))
    return hashid_df.set_index('hashid')


def add_sources(match_df, waveform_order, dbdir):
    hash_df = pd.read_csv('%s/resample_ssf.hashid.%s.xz' % (dbdir, waveform_order), engine='pyarrow', index_col='hashid')
    match_df = match_df.join(hash_df)
    match_df['sources'] = match_df['sources'].apply(ast.literal_eval)
    return match_df



def describe_matches(match_df, waveform_order, dbdir):
    sidinfo = pd.read_csv('%s/sidinfo.csv' % dbdir)
    sidinfo['path'] = sidinfo['path'].apply(lambda x: x[:-4]) 
    match_df = add_sources(match_df, waveform_order, dbdir)
    sources = set()
    for row in match_df.itertuples():
        for source in row.sources:
            print('%s/%s.%d.wav' % (dbdir, source, row.Index))
            sources .add(source)
    print(sidinfo[sidinfo.path.isin(sources)][['path', 'ReleasedYear']])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('waveform_order', type=str)
    parser.add_argument('hashid', type=int)
    parser.add_argument('--dbdir', type=str, default='hvsc-76')
    args = parser.parse_args()
    df, match_cols = read_dfs(args.waveform_order, args.dbdir)
    match_df = fuzzy_match(args.hashid, df, match_cols)
    describe_matches(match_df, args.waveform_order, args.dbdir)


if __name__ == '__main__':
    main()
