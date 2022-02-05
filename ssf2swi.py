#!/usr/bin/python3

import argparse
import pandas as pd
from sidlib import resampledf_to_pr, get_sid, CONTROL_BITS, timer_args, timer_args, timer_args, timer_args
from ssf import add_freq_notes_df


# -8369400230369463243, C64Music/MUSICIANS/H/Hubbard_Rob/Commando.ssf.xz
# -6332327843409751282, C64Music/MUSICIANS/L/Linus/Ride_the_High_Country.ssf.xz
parser = argparse.ArgumentParser(description='Transcribe SSF to Sid Wizard instrument')
parser.add_argument('--ssffile', help='SSF file', default='C64Music/MUSICIANS/L/Linus/Ride_the_High_Country.ssf.xz')
parser.add_argument('--hashid', type=int, help='hashid to transcribe', default=-6332327843409751282)
timer_args(parser)

args = parser.parse_args()
sid = get_sid(args.pal)


def dot0(hexval):
    val = [(hexval[i:i+2]) for i in range(0, len(hexval), 2)]
    val = ['..' if i == '00' else i for i in val]
    return ''.join(val)


def wf_from_row(row):
    val = 0
    for b, col in enumerate(CONTROL_BITS):
        col_val = getattr(row, col + '1', 0)
        if pd.notna(col_val) and col_val:
            val += 2**b
    return '%2.2X' % val


def arp_from_row(row):
    arp = getattr(row, 'freq1', 0)
    val = 0
    if pd.notna(arp):
        val = row.closest_note - 12 + 0x81
    return '%2.2X' % val


def pulse_from_row(row):
    pwduty = getattr(row, 'pwduty1', 0)
    val = 0
    if pd.notna(pwduty):
        val = pwduty | 0x8000
    return '%4.4X' % val


def filter_from_row(row):
    val = 0
    route_map = {
        (0, 0, 0): 0x8,
        (1, 0, 0): 0x9,
        (1, 1, 0): 0xb,
        (0, 0, 1): 0xc,
        (1, 0, 1): 0xd,
        (0, 1, 1): 0xe,
        (1, 1, 1): 0xf,
    }

    if pd.notna(row.flt1) and row.flt1:
        coff = row.fltcoff
        res = row.fltres
        route = route_map.get((row.fltlo, row.fltband, row.flthi)) << 4
        val = ((route + res) << 8) + (coff & 0xff)

    return '%4.4X' % val


df = pd.read_csv(args.ssffile, dtype=pd.Int64Dtype())
ssf_df = df[df.hashid == args.hashid].drop(['clock', 'hashid_noclock', 'count', 'rate', 'vol', 'vbi_frame', 'hashid', 'fltext'], axis=1)
ssf_df = resampledf_to_pr(sid, ssf_df).reset_index(drop=True)

atk1, dec1, sus1, rel1, pr_speed, test1_initial = ssf_df[['atk1', 'dec1', 'sus1', 'rel1', 'pr_speed', 'test1']].iloc[0]
ssf_df = ssf_df.drop(['atk1', 'dec1', 'sus1', 'rel1', 'pr_speed'], axis=1)

if atk1 == 0:
    first_freq = ssf_df.index[ssf_df['freq1'].notna()][0]
    ssf_df = ssf_df[first_freq:]
    ssf_df['pr_frame'] = ssf_df['pr_frame'] - ssf_df['pr_frame'].min()

ssf_df = ssf_df.set_index('pr_frame')
ssf_df = add_freq_notes_df(sid, ssf_df)
ssf_df['real_freq'] = ssf_df['real_freq'].round(2)

ssf_df['F'] = ssf_df.apply(lambda x: '%2.2X' % x.name, axis=1)
ssf_df['WF'] = ssf_df.apply(wf_from_row, axis=1)
ssf_df['ARP'] = ssf_df.apply(arp_from_row, axis=1)
ssf_df['PULSE'] = ssf_df.apply(pulse_from_row, axis=1)
ssf_df['FILT'] = ssf_df.apply(filter_from_row, axis=1)
ssf_df[['ARP', 'PULSE', 'FILT']] = ssf_df[['ARP', 'PULSE', 'FILT']].apply(
    lambda row: [dot0(c) for c in row])

print('multispeed: %u' % pr_speed)

adsr = '%X%X%X%X' % (atk1, dec1, sus1, rel1)
print('ADSR: %s' % adsr)
if test1_initial:
    print('ADHR: %s' % adsr)

print()
pd.set_option('display.max_rows', None)
print(ssf_df)
