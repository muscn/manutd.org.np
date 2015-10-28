from collections import OrderedDict
import datetime
from datetime import timedelta
from random import randint
import urllib
import json

import wikipedia
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile

from django.core.urlresolvers import reverse_lazy, reverse
from django.db import models
from django.db.models import Count
from jsonfield import JSONField
from django.conf import settings
import pytz as pytz

from muscn.utils.countries import CountryField
from muscn.utils.forms import unique_slugify
from muscn.utils.npt import utc_to_local

from django.core.cache import cache
from django.db.models import Q

YEAR_CHOICES = []
for r in range(1890, (datetime.datetime.now().year + 1)):
    YEAR_CHOICES.append((r, r))


# Fixtured
class Competition(models.Model):
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=10, null=True, blank=True)
    slug = models.SlugField(max_length=255)
    order = models.IntegerField(default=0)

    def get_short_name(self):
        if self.short_name:
            return self.short_name
        return self.name

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ('order',)


class CompetitionYear(models.Model):
    competition = models.ForeignKey(Competition, related_name='seasons')
    year = models.IntegerField('Year', choices=YEAR_CHOICES, default=datetime.datetime.now().year)

    def __unicode__(self):
        return unicode(self.competition) + ' - ' + unicode(self.year)

    class Meta:
        ordering = ('competition__order',)


# # Fixtured
# class Country(models.Model):
# name = models.CharField(max_length=255)
# slug = models.SlugField(max_length=255)


# Fixtured
class City(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    country = CountryField()

    class Meta:
        verbose_name_plural = 'Cities'


# Fixtured
class Stadium(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True, null=True)
    city = models.ForeignKey(City, related_name='stadiums', blank=True, null=True)
    capacity = models.PositiveIntegerField(blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    image = models.ImageField(upload_to='stadiums/', blank=True, null=True)

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        unique_slugify(self, self.name)
        super(Stadium, self).save(*args, **kwargs)


# Fixtured
class Team(models.Model):
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=10, blank=True, null=True)
    alternative_names = models.CharField(max_length=255, blank=True, null=True)
    nick_name = models.CharField(max_length=50, blank=True, null=True)
    stadium = models.ForeignKey(Stadium, related_name='teams', blank=True, null=True)
    foundation_date = models.DateField(blank=True, null=True)
    crest = models.FileField(upload_to='crests/', blank=True, null=True)
    color = models.CharField(max_length=255, blank=True, null=True)
    wiki = models.CharField(max_length=255, blank=True, null=True)

    def get_wiki(self):
        if not self.wiki:
            search_results = wikipedia.search(self.name + ' football club', results=1)
            if not search_results:
                return None
            self.wiki = search_results[0]
            self.save()
        return self.wiki

    def get_crest(self):
        if not self.crest:
            wiki = self.get_wiki()
            url = 'https://en.wikipedia.org/w/api.php?action=query&titles=' + wiki + '&prop=pageimages&format=json&pithumbsize=200'
            image_data = json.loads(urllib.urlopen(url).read())
            data = image_data['query']['pages'].itervalues().next()
            image_name = data['pageimage'] + '.png'
            image_url = data['thumbnail']['source']
            img_temp = NamedTemporaryFile(delete=True)
            img_temp.write(urllib.urlopen(image_url).read())
            img_temp.flush()
            self.crest.save(image_name, File(img_temp))
        return self.crest

    def get_crest_url(self):
        if self.get_crest():
            return self.crest.url
        return None

    def __unicode__(self):
        return self.name

    def get_derby_teams(self):
        # stadium -> city -> stadiums -> teams
        pass

    def get_current_players(self):
        pass

    def get_current_staffs(self):
        pass

    def get_players_by_year(self, year):
        pass

    def get_staffs_by_year(self, year):
        pass

    @classmethod
    def get(cls, name):
        try:
            return Team.objects.get(name=name)
        except Team.DoesNotExist:
            return Team.objects.get(alternative_names__icontains='|' + name + '|')


class TeamYear(models.Model):
    team = models.ForeignKey(Team, related_name='seasons')
    year = models.IntegerField('Year', choices=YEAR_CHOICES)
    # color codes, hex probably
    home_color = models.CharField(max_length=10, null=True, blank=True)
    away_color = models.CharField(max_length=10, null=True, blank=True)
    third_color = models.CharField(max_length=10, null=True, blank=True)


class Person(models.Model):
    name = models.CharField(max_length=254)
    slug = models.SlugField(max_length=254, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    image = models.ImageField(upload_to='photos/', blank=True, null=True)
    height = models.FloatField(blank=True, null=True)
    weight = models.FloatField(blank=True, null=True)
    birth_place = models.CharField(max_length=255, blank=True, null=True)

    def save(self, *args, **kwargs):
        unique_slugify(self, self.name)
        super(Person, self).save(*args, **kwargs)

    # fmh
    # favored_person = models.ForeignKey('Person')
    # favored_team = models.ForeignKey(Team)

    def __unicode__(self):
        return self.name

    class Meta:
        abstract = True


class Player(Person):
    squad_no = models.PositiveIntegerField(blank=True, null=True)
    nationality = CountryField()
    favored_position = models.CharField(max_length=4, blank=True, null=True)
    previous_club = models.CharField(max_length=255, blank=True, null=True)
    on_loan = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    def get_absolute_url(self):
        return reverse('view_player', kwargs={'slug': self.slug})

    def get_contract_expiry_date(self):
        pass

    def get_current_team(self):
        pass


class Official(Person):
    nationality = CountryField(null=True, blank=True)
    pass


# Doesn't handle cases where a player is also a staff. e.g.: Giggsy 2013/14 :D
class Staff(Person):
    nationality = CountryField()
    roles = [('Manager', 'manager'), ('Goal Keeping Coach', 'goal_keeping_coach')]
    role = models.CharField(max_length=254, choices=roles)

    def get_contract_expiry_date(self):
        pass

    def get_current_team(self):
        pass


class PlayerCareerSession(models.Model):
    player = models.ForeignKey(Player, related_name='career_sessions')
    team = models.ForeignKey(Team, related_name='player_sessions')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    wage = models.FloatField(null=True, blank=True)

    @property
    def session_expired(self):
        # return False if not self.end_date or if self.end_date is in future
        pass


class StaffCareerSession(models.Model):
    staff = models.ForeignKey(Staff, related_name='career_sessions')
    team = models.ForeignKey(Team, related_name='staff_sessions')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    wage = models.FloatField(null=True, blank=True)

    @property
    def session_expired(self):
        # return False if not self.end_date or if self.end_date is in future
        pass


class Match(models.Model):
    start_time = models.DateTimeField()
    home_team = models.ForeignKey(Team, related_name='home_matches')
    away_team = models.ForeignKey(Team, related_name='away_matches')
    competition_year = models.ForeignKey(CompetitionYear, related_name='matches')
    referee = models.ForeignKey(Official, related_name='refereed_matches', blank=True, null=True)
    assistant_referee_1 = models.ForeignKey(Official, related_name='assisted_matches', blank=True, null=True)
    assistant_referee_2 = models.ForeignKey(Official, related_name='assisted_matches2', blank=True, null=True)
    match_referee = models.ForeignKey(Official, blank=True, null=True)


# Match Events

# class Card(models.Model):
# player = models.ForeignKey(Player)
# time = models.PositiveIntegerField()
# match = models.ForeignKey(Match)
#
# class Meta:
# abstract = True


class YellowCard(models.Model):
    player = models.ForeignKey(Player, related_name='yellow_cards')
    time = models.PositiveIntegerField()
    match = models.ForeignKey(Match, related_name='yellow_cards')


class RedCard(models.Model):
    player = models.ForeignKey(Player, related_name='red_cards')
    time = models.PositiveIntegerField()
    match = models.ForeignKey(Match, related_name='red_cards')


class Substitution(models.Model):
    subbed_in = models.ForeignKey(Player, related_name='subbed_in')
    subbed_out = models.ForeignKey(Player, related_name='subbed_out')
    types = [('Injury', 'injury'), ('Tactical', 'tactical')]
    type = models.CharField(max_length=10, choices=types, null=True, blank=True)
    time = models.PositiveIntegerField()


# Pure stats

class StatSet(models.Model):
    """
    Holds all the basic stats of a game such as possession, shots on goal
    so on and so forth
    """

    attempts_on_goal = models.IntegerField()
    shots_on_target = models.IntegerField()
    shots_off_target = models.IntegerField()
    blocked_shots = models.IntegerField()
    corner_kicks = models.IntegerField()
    fouls = models.IntegerField()
    crosses = models.IntegerField()
    offsides = models.IntegerField()
    first_yellows = models.IntegerField()
    second_yellows = models.IntegerField()
    red_cards = models.IntegerField()
    duels_won = models.IntegerField()
    duels_won_percentage = models.IntegerField()
    total_passes = models.IntegerField()
    pass_percentage = models.IntegerField()
    possession = models.DecimalField(decimal_places=2, max_digits=4)
    team = models.ForeignKey(Team)
    match = models.ForeignKey(Match, related_name='stats')

    def __unicode__(self):
        return u'Stats for %s' % self.match


# class PlayerStatLine(models.Model):
# """ Used for collecting the stat line for a player in a game """
#
# player = models.ForeignKey(Player)
# match = models.ForeignKey(Match)
# shots = models.IntegerField(default=0)
# shots_on_goal = models.IntegerField(default=0)
# minutes = models.IntegerField(default=0)
# goals = models.IntegerField(default=0)
# assists = models.IntegerField(default=0)
# fouls_committed = models.IntegerField(default=0)
# fouls_suffered = models.IntegerField(default=0)
# corners = models.IntegerField(default=0)
# offsides = models.IntegerField(default=0)
# saves = models.IntegerField(default=0)
# goals_against = models.IntegerField(default=0)
#
# def __unicode__(self):
# return u'Stats for %s' % self.player

# Formation
# Position


class Injury(models.Model):
    player = models.ForeignKey(Player, related_name='injuries')
    # injuries = [('Groin', 'Groin'), ('Hamstring', 'Hamstring'), ('MCL', 'MCL'), ('ACL', 'ACL')]
    # Ankle, Illness, Shoulder, Finger,
    type = models.CharField(max_length=100, null=True, blank=True)
    injury_date = models.DateField(null=True, blank=True)
    return_date = models.DateField(null=True, blank=True)
    return_date_confirmed = models.BooleanField(default=False)
    remarks = models.CharField(max_length=255, null=True, blank=True)

    @classmethod
    def get_current_injuries(cls):
        return Injury.objects.filter(
            Q(return_date__gte=datetime.date.today()) | Q(return_date__isnull=datetime.date.today())).order_by(
            'return_date').select_related()

    @classmethod
    def get_past_injuries(cls):
        return Injury.objects.filter(return_date__lt=datetime.date.today()).order_by('-return_date').select_related()

    class Meta:
        verbose_name_plural = 'Injuries'

    def __unicode__(self):
        return unicode(self.player) + ' - ' + unicode(self.type)


class Quote(models.Model):
    text = models.TextField()
    by = models.CharField(max_length=255, null=True, blank=True)
    enabled = models.BooleanField(default=True)

    def excerpt(self):
        txt = self.text
        if len(txt) < 101:
            return txt
        return txt[0:98] + ' ...'

    @classmethod
    def random(cls):
        count = cls.objects.aggregate(count=Count('id'))['count']
        if not count:
            return None
        random_index = randint(0, count - 1)
        return cls.objects.all()[random_index]

    def __unicode__(self):
        return unicode(self.by) + ' : ' + self.excerpt()


class SeasonData(models.Model):
    year = models.IntegerField('Year', choices=YEAR_CHOICES)
    summary = JSONField(blank=True, null=True)

    @property
    def gd(self):
        return int(self.summary['F']) - int(self.summary['A'])

    @property
    def slug(self):
        return str(self.year) + '-' + str("{0:02d}".format(int(str(self.year + 1)[-2:])))

    def get_absolute_url(self):
        return reverse_lazy('view_seasondata', kwargs={'year': self.year, 'year1': str(self.year + 1)[-2:]})

    def __unicode__(self):
        return unicode(self.slug)

    class Meta:
        verbose_name_plural = 'Seasons Data'
        ordering = ('-year',)


class CompetitionYearMatches(models.Model):
    competition_year = models.ForeignKey(CompetitionYear)
    matches_data = JSONField()

    def __unicode__(self):
        return unicode(self.competition_year)


class Fixture(models.Model):
    opponent = models.ForeignKey(Team)
    is_home_game = models.BooleanField(default=True)
    datetime = models.DateTimeField()
    competition_year = models.ForeignKey(CompetitionYear)
    round = models.CharField(max_length=255, blank=True, null=True)
    venue = models.CharField(max_length=255, blank=True, null=True, help_text='Leave blank for auto-detection')
    broadcast_on = models.CharField(max_length=255, blank=True, null=True)
    mufc_score = models.PositiveIntegerField(null=True, blank=True)
    opponent_score = models.PositiveIntegerField(null=True, blank=True)
    remarks = models.CharField(max_length=255, null=True, blank=True)

    @classmethod
    def get_upcoming(cls):
        return cls.objects.filter(datetime__gt=datetime.datetime.now()).order_by('datetime').select_related()

    @classmethod
    def results(cls):
        return cls.objects.filter(datetime__lt=datetime.datetime.now()).order_by('-datetime').select_related()

    @classmethod
    def recent_results(cls):
        return cls.objects.filter(datetime__lt=datetime.datetime.now()).order_by('-datetime')[0:5].select_related()

    def score(self):
        if self.is_home_game:
            return 'Man United ' + unicode(self.mufc_score) + ' - ' + unicode(self.opponent_score) + ' ' + unicode(
                self.opponent)
        else:
            return unicode(self.opponent) + ' ' + unicode(self.opponent_score) + ' - ' + unicode(
                self.mufc_score) + ' Man United'

    def result(self):
        if self.mufc_score == self.opponent_score:
            return 0
        elif self.mufc_score > self.opponent_score:
            return 1
        else:
            return -1

    @classmethod
    def get_next_match(cls):
        try:
            return cls.objects.filter(datetime__gt=datetime.datetime.now()).order_by('datetime')[:1].select_related()[0]
        except IndexError:
            return None

    def npt(self):
        return utc_to_local(self.datetime)

    def time_remaining(self):
        now = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
        delta = self.datetime - now
        dhm = (delta.days, delta.seconds // 3600, (delta.seconds // 60) % 60)
        return dhm

    @property
    def title(self):
        if self.is_home_game:
            return 'Man United vs. ' + unicode(self.opponent)
        else:
            return unicode(self.opponent) + ' vs. Man United'

    def get_venue(self):
        if self.venue:
            return self.venue
        elif self.is_home_game:
            return 'Old Trafford'
        else:
            return self.opponent.stadium.name

    def __unicode__(self):
        # return self.title
        ret = 'vs. ' + unicode(self.opponent) + ' at ' + self.get_venue()
        # if datetime.datetime.now() > self.datetime:
        #     ret += '[PAST] '
        return ret

    class Meta:
        ordering = ('datetime',)


class Goal(models.Model):
    scorer = models.ForeignKey(Player, related_name='goals')
    assist_by = models.ForeignKey(Player, related_name='assists', blank=True, null=True)
    penalty = models.BooleanField(default=False)
    own_goal = models.BooleanField(default=False)
    time = models.PositiveIntegerField(blank=True, null=True)
    match = models.ForeignKey(Fixture, related_name='goals')

    def __unicode__(self):
        ret_str = unicode(self.scorer) + ' against ' + unicode(self.match.opponent)
        if self.time:
            ret_str = ret_str + ' at ' + unicode(self.time) + "'"
        return ret_str


class MatchResult(models.Model):
    fixture = models.ForeignKey(Fixture)
    mufc_score = models.PositiveIntegerField(default=0)
    opponent_score = models.PositiveIntegerField(default=0)

    @property
    def title(self):
        if self.fixture.is_home_game:
            return 'Man United ' + unicode(self.mufc_score) + ' - ' + unicode(self.opponent_score) + ' ' + unicode(
                self.fixture.opponent)
        else:
            return unicode(self.fixture.opponent) + ' ' + unicode(self.opponent_score) + ' - ' + unicode(
                self.mufc_score) + ' ' + 'Man United'

    def __unicode__(self):
        return unicode(self.fixture.title)


class PlayerSocialAccount(models.Model):
    player = models.OneToOneField(Player, related_name='social_accounts')
    twitter = models.CharField(max_length=100, blank=True, null=True, help_text='Username')
    instagram = models.CharField(max_length=100, blank=True, null=True, help_text='Username')
    facebook = models.CharField(max_length=100, blank=True, null=True, help_text='Username')
    youtube = models.URLField(max_length=255, blank=True, null=True, help_text='URL')
    website = models.URLField(max_length=255, blank=True, null=True, help_text='URL')

    def __str__(self):
        return str(self.player) + ' on Social Media'


def get_top_scorers():
    from django.conf import settings

    goals = Goal.objects.all().select_related()
    competition_years = CompetitionYear.objects.all().select_related()
    competition_dct = OrderedDict()
    competitions = OrderedDict()
    for competition_year in competition_years:
        if competition_year.year == settings.YEAR:
            competition_dct[competition_year.competition_id] = 0
            competitions[competition_year.competition_id] = competition_year.competition.name
    players = OrderedDict()
    for goal in goals:
        competition_id = goal.match.competition_year.competition_id
        if goal.scorer not in players:
            players[goal.scorer] = {}
            players[goal.scorer]['competitions'] = competition_dct.copy()
            players[goal.scorer]['total'] = 0
        players[goal.scorer]['competitions'][competition_id] += 1
        players[goal.scorer]['total'] += 1
    players = OrderedDict(sorted(players.items(), key=lambda item: item[1]['total'], reverse=True))
    context = {
        'players': players,
        'competitions': competitions
    }
    return context


def get_top_scorers_summary():
    goals = Goal.objects.all().select_related()
    players = OrderedDict()
    for goal in goals:
        if goal.scorer not in players:
            players[goal.scorer] = 0
        players[goal.scorer] += 1
    players = OrderedDict(sorted(players.items(), key=lambda item: item[1], reverse=True))
    return players


def get_latest_epl_standings():
    print datetime.datetime.now().isoformat()
    print 'Retrieving table from API'
    link = 'http://football-api.com/api/?Action=standings&comp_id=1204&APIKey=' + settings.FOOTBALL_API_KEY
    f = urllib.urlopen(link)
    standings = f.read()
    standings_loaded = json.loads(standings)
    print standings_loaded['ERROR']
    cache.set('epl_standings', standings_loaded, timeout=None)
    return standings_loaded
