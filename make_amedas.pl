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

foreach my $code (sort keys %maps) {
    my $point = $maps{$code};

    if ($dups{$point} > 1) {
        print "$maps{$code} $code $prefs{$code}\n";
    } else {
        print "$maps{$code} $code\n";
    }
}
