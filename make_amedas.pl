#!/usr/bin/perl

use utf8;
use strict;
use warnings;
use LWP::UserAgent;
use Archive::Zip ':ERROR_CODES';
use Encode 'decode';

my %prefs;      # 都道府県地方名
my %maps;       # 観測所コードと観測所名
my %dups;       # 観測所名重複用

my $zip = 'ame_master.zip';
my $csv = 'ame_master.csv';

my $ua = LWP::UserAgent->new;
my $res = $ua->mirror('http://www.jma.go.jp/jma/kishou/know/amedas/' . $zip, $zip);
if ($res->code == 200) {
    my $z = Archive::Zip->new;
    $z->read($zip) == AZ_OK || die $!;

    foreach my $member ($z->members) {
        $z->extractMemberWithoutPaths($member->fileName());
    }
}

open(my $fd, '<', $csv) || die $!;
<$fd>;
while (my $line = <$fd>) {
    $line = Encode::decode('sjis', $line);
    utf8::encode($line);

    my ($pref, $code, undef, $point) = split(',', $line);
    next if defined $maps{$code};

    $maps{$code} = $point;
    $prefs{$code} = $pref;
    $dups{$point}++;
}
close($fd);

my %table = (
    'ケ' => 'ヶ',
    'ヶ' => 'ケ',
    '鰺' => '鯵',
);

sub _trans {
    my $point = shift;
    my @results = ();

    utf8::decode($point);

    foreach my $p (keys %table) {
        if ($point =~ /$p/) {
            my $tmp = $point;

            $tmp =~ s/$p/$table{$p}/;
            utf8::encode($tmp);
            push @results, $tmp;
        }
    }
    @results;
}

sub trans {
    my $word = shift;

    my @results = ($word);
    my @r = _trans($word);
    for my $r (@r) {
        push @results, $r;
        my @_r = _trans($r);
        push @results, @_r;
    }
    my %hash;
    map {$hash{$_}++ unless $hash{$_}} @results;
    sort keys %hash;
}

foreach my $code (sort keys %maps) {
    my $point = $maps{$code};

    if ($dups{$point} > 1) {
        foreach my $kpoint (trans($point)) {
            print "$kpoint $code $prefs{$code}\n";
        }
    } else {
        foreach my $kpoint (trans($point)) {
            print "$kpoint $code\n";
        }
    }
}
