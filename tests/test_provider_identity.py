from datetime import date,datetime,timezone,timedelta
from uuid import uuid4
import pytest
from astock.data.provider_identity import ListingEpisode,ExchangeCode,ProviderBinding,SourceObservation,ProviderResolver

NOW=datetime(2026,10,2,tzinfo=timezone.utc)
DAY=date(2025,4,30)


def fixture(*,switch=date(2025,5,6),venue='BSE',native='920001.BJ',dataset='daily',start=date(2021,11,15),asset='STK'):
    episode=ListingEpisode(episode_id=uuid4(),security_id='synthetic-security',venue=venue,asset_type=asset,
        valid_from=start,retrieved_at=NOW,available_at=NOW,evidence_ids=('synthetic-official-event',),approval_ref='synthetic-review')
    old=ExchangeCode(code_id=uuid4(),episode_id=episode.episode_id,identifier='830001.BJ',valid_from=start,
        valid_to=switch,available_at=NOW,evidence_ids=('synthetic-old-code',),approval_ref='synthetic-review')
    new=old.model_copy(update=dict(code_id=uuid4(),identifier=native,valid_from=switch,valid_to=None))
    observation=SourceObservation(raw_object_id=uuid4(),raw_row_number=0,event_date=DAY)
    binding=ProviderBinding(binding_id=uuid4(),binding_version=1,dataset=dataset,native_identifier=native,
        episode_id=episode.episode_id,representation_kind='RETROSPECTIVE',observations=(observation,),
        first_observed_at=NOW-timedelta(days=1),decision_at=NOW,available_at=NOW,evidence_ids=('synthetic-capture',),
        decision_status='APPROVED',approval_ref='synthetic-review')
    return episode,[old,new],binding


def resolve(resolver,binding,**changes):
    o=binding.observations[0]
    args=dict(provider='tushare',dataset=binding.dataset,native_identifier=binding.native_identifier,
        event_date=o.event_date,raw_object_id=o.raw_object_id,raw_row_number=o.raw_row_number,knowledge_as_of=NOW)
    args.update(changes)
    return resolver.resolve(**args)


@pytest.mark.parametrize('switch',[date(2025,5,6),date(2025,10,9)])
def test_official_transition_does_not_change_retrospective_native(switch):
    e,c,b=fixture(switch=switch)
    r=ProviderResolver([e],c,[b]);hit=resolve(r,b)
    assert hit.reason is None and hit.native_identifier=='920001.BJ'
    assert hit.exchange_code_at_event=='830001.BJ'
    o=b.observations[0].model_copy(update={'event_date':switch})
    after=b.model_copy(update={'binding_id':uuid4(),'observations':(o,)})
    assert resolve(ProviderResolver([e],c,[after]),after).exchange_code_at_event=='920001.BJ'


@pytest.mark.parametrize('changes',[
    {'dataset':'stock_st'}, {'dataset':'unknown'}, {'provider':'other'},
    {'raw_object_id':uuid4()}, {'raw_row_number':1}, {'event_date':date(2025,5,1)},
    {'knowledge_as_of':NOW-timedelta(microseconds=1)}])
def test_dataset_capture_event_and_knowledge_scope_never_fallback(changes):
    e,c,b=fixture();assert resolve(ProviderResolver([e],c,[b]),b,**changes).reason=='NO_SCOPED_PROVIDER_BINDING'


def test_event_native_stock_st_and_retrospective_daily_are_separate():
    e,c,b=fixture();o=b.observations[0]
    st=b.model_copy(update=dict(binding_id=uuid4(),dataset='stock_st',native_identifier='830001.BJ',representation_kind='EVENT_NATIVE'))
    resolver=ProviderResolver([e],c,[b,st])
    assert resolve(resolver,st).reason is None
    assert resolve(resolver,b,dataset='stock_st').reason=='NO_SCOPED_PROVIDER_BINDING'


@pytest.mark.parametrize('native',['T600018.SH','T00018.SH',' 920001.BJ','NA'])
def test_provider_native_retention_does_not_normalize(native):
    e,c,b=fixture();b=b.model_copy(update={'native_identifier':native})
    hit=resolve(ProviderResolver([e],c,[b]),b)
    assert hit.reason=='NON_NORMALIZED_IDENTIFIER' and hit.native_identifier==native


def test_missing_native_retained():
    e,c,b=fixture();hit=resolve(ProviderResolver([e],c,[b]),b,native_identifier=None)
    assert hit.reason=='MISSING_NATIVE_IDENTIFIER' and hit.native_identifier is None


def test_venue_interval_and_pre_bse_cannot_be_extended_by_native():
    e,c,b=fixture();e=e.model_copy(update={'valid_from':date(2025,5,6)})
    assert resolve(ProviderResolver([e],[c[1]],[b]),b).reason=='OUTSIDE_LISTING_EPISODE'
    e,c,b=fixture(start=date(2020,1,1))
    b=b.model_copy(update={'observations':(b.observations[0].model_copy(update={'event_date':date(2021,11,12)}),)})
    assert resolve(ProviderResolver([e],c,[b]),b).reason=='PRE_BSE_LEGACY'


def test_two_candidates_conflict_even_same_security_or_different_episode():
    e,c,b=fixture();other=b.model_copy(update={'binding_id':uuid4()})
    with pytest.raises(ValueError,match='Overlapping'):ProviderResolver([e],c,[b,other])
    e2=e.model_copy(update={'episode_id':uuid4()});other=other.model_copy(update={'episode_id':e2.episode_id})
    with pytest.raises(ValueError,match='Overlapping'):ProviderResolver([e,e2],c,[b,other])


def test_code_reuse_requires_distinct_episode_and_disjoint_official_intervals():
    e,c,b=fixture();e2=e.model_copy(update={'episode_id':uuid4(),'security_id':'unrelated-security','valid_from':date(2030,1,1)})
    c2=c[1].model_copy(update={'code_id':uuid4(),'episode_id':e2.episode_id,'valid_from':date(2030,1,1)})
    with pytest.raises(ValueError,match='official'):ProviderResolver([e,e2],[*c,c2],[b])
    old=c[1].model_copy(update={'valid_to':date(2030,1,1)})
    e=e.model_copy(update={'valid_to':date(2030,1,1)})
    assert resolve(ProviderResolver([e,e2],[c[0],old,c2],[b]),b).security_id=='synthetic-security'


def test_approved_supersession_asof_and_proposed_version_is_inactive():
    e,c,b=fixture();later=NOW+timedelta(days=1)
    correction=b.model_copy(update=dict(binding_id=uuid4(),binding_version=2,supersedes_binding_id=b.binding_id,
        decision_at=later,available_at=later,observations=(b.observations[0].model_copy(update={'raw_row_number':1}),)))
    r=ProviderResolver([e],c,[b,correction])
    assert resolve(r,b).binding_id==b.binding_id
    assert resolve(r,b,knowledge_as_of=later).reason=='NO_SCOPED_PROVIDER_BINDING'
    proposed=correction.model_copy(update={'decision_status':'PROPOSED','approval_ref':None})
    assert resolve(ProviderResolver([e],c,[b,proposed]),b,knowledge_as_of=later).binding_id==b.binding_id
    fork=correction.model_copy(update={'binding_id':uuid4()})
    with pytest.raises(ValueError,match='forked'):ProviderResolver([e],c,[b,correction,fork])


@pytest.mark.parametrize('changes,reason',[
    ({'provider_exchange':'SSE'},'PROVIDER_EXCHANGE_CONFLICT'),
    ({'provider_asset_type':'BOND'},'PROVIDER_ASSET_CONFLICT')])
def test_explicit_provider_semantic_conflicts(changes,reason):
    e,c,b=fixture();assert resolve(ProviderResolver([e],c,[b]),b,**changes).reason==reason


@pytest.mark.parametrize('asset,reason',[('UNKNOWN','ASSET_EVIDENCE_REQUIRED'),('BOND','ASSET_OUT_OF_SCOPE'),('CDR','ASSET_OUT_OF_SCOPE')])
def test_unknown_and_non_stock_assets_never_guessed(asset,reason):
    e,c,b=fixture(asset=asset);assert resolve(ProviderResolver([e],c,[b]),b).reason==reason


def test_limit_requires_explicit_asset():
    e,c,b=fixture(dataset='stk_limit');r=ProviderResolver([e],c,[b])
    assert resolve(r,b).reason=='ASSET_EVIDENCE_REQUIRED'
    assert resolve(r,b,provider_asset_type='STK',provider_exchange='BSE').reason is None


def test_model_rejects_wildcards_duplicate_scope_and_backdated_approval():
    e,c,b=fixture();payload=b.model_dump()
    for change in ({'dataset':'*'},{'observations':(b.observations[0],b.observations[0])},
                   {'available_at':NOW-timedelta(days=2)},{'approval_ref':None}):
        with pytest.raises(ValueError):ProviderBinding.model_validate({**payload,**change})
    with pytest.raises(ValueError):ProviderResolver([e],c,[b]).resolve(provider='tushare',dataset='daily',
        native_identifier=b.native_identifier,event_date=DAY,raw_object_id=b.observations[0].raw_object_id,
        raw_row_number=0,knowledge_as_of=datetime(2026,10,2))


def test_overlap_listing_episodes_without_bindings_is_conflict():
    e,c,b=fixture()
    other=e.model_copy(update={'episode_id':uuid4(),'venue':'SSE'})
    with pytest.raises(ValueError,match='Overlapping listing'):ProviderResolver([e,other],[],[])


def test_event_native_cannot_mean_retrospective_code():
    e,c,b=fixture();b=b.model_copy(update={'representation_kind':'EVENT_NATIVE'})
    assert resolve(ProviderResolver([e],c,[b]),b).reason=='EVENT_NATIVE_OFFICIAL_CODE_CONFLICT'
