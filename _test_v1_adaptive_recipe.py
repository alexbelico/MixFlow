import MixFlowAssistant as m

bass_heavy={
 'spectrum':{'bass_60_150':0.34,'lowmid_150_350':0.30,'presence_2k_5k':0.12,'air_8k_16k':0.04},
 'loudness':{'input_lra':'9.5'},'crest_factor_db':15.0,'dc_offset':0.002
}
filters=m.adaptive_mix_filters(bass_heavy)
for token in ['highpass=f=28:p=2','equalizer=f=95','equalizer=f=240','equalizer=f=2800','equalizer=f=10000','acompressor=','dcshift=']:
    assert any(token in f for f in filters),(token,filters)
balanced={'spectrum':{'bass_60_150':0.20,'lowmid_150_350':0.20,'presence_2k_5k':0.20,'air_8k_16k':0.10},'loudness':{'input_lra':'4.0'},'crest_factor_db':8.0,'dc_offset':0.0001}
filters2=m.adaptive_mix_filters(balanced)
assert filters2==['highpass=f=28:p=2'],filters2
print('PASS ADAPTIVE_RECIPE_TARGETED',filters)
print('PASS ADAPTIVE_RECIPE_CONSERVATIVE',filters2)
