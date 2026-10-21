import MixFlowAssistant as m

def sample(i,tp,lra,crest):
    return {'loudness':{'input_i':str(i),'input_tp':str(tp),'input_lra':str(lra)},'crest_factor_db':crest}
assert m.recommend_loudness(sample(-6.0,0.2,5,9))==('1',-14.0,'Light')
assert m.recommend_loudness(sample(-14.0,-1.5,13,12))==('2',-12.0,'Básico')
assert m.recommend_loudness(sample(-22.0,-3.0,5,8))==('3',-10.0,'Habitual')
assert m.recommend_loudness(None)==('3',-10.0,'Habitual')
print('PASS LOUDNESS_RECOMMENDATION_CASES')
