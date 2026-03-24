import pandas as pd
import numpy as np

class AlphaLibrary:
    def __init__(self, engine):
        self.e = engine

    def get_alpha_001(self):
        """rank(Ts_ArgMax(SignedPower(((returns < 0) ? stddev(returns, 20) : close), 2.), 5)) - 0.5"""
        inner = self.e.close.copy()
        inner[self.e.returns < 0] = self.e.ts_std(self.e.returns, 20)
        return self.e.rank(self.e.ts_argmax(self.e.power(inner, 2), 5)) - 0.5

    def get_alpha_002(self):
        """(-1 * correlation(rank(delta(log(volume), 2)), rank(((close - open) / open)), 6))"""
        return -1 * self.e.correlation(self.e.rank(self.e.delta(self.e.log(self.e.volume), 2)), 
                                        self.e.rank((self.e.close - self.e.open) / self.e.open), 6)

    def get_alpha_003(self):
        """(-1 * correlation(rank(open), rank(volume), 10))"""
        return -1 * self.e.correlation(self.e.rank(self.e.open), self.e.rank(self.e.volume), 10)

    def get_alpha_004(self):
        """(-1 * Ts_Rank(rank(low), 9))"""
        return -1 * self.e.ts_rank(self.e.rank(self.e.low), 9)

    def get_alpha_005(self):
        """(rank((open - (sum(vwap, 10) / 10))) * (-1 * abs(rank((close - vwap)))))"""
        return self.e.rank(self.e.open - (self.e.ts_mean(self.e.vwap, 10))) * (-1 * self.e.abs(self.e.rank(self.e.close - self.e.vwap)))

    def get_alpha_006(self):
        """(-1 * correlation(open, volume, 10))"""
        return -1 * self.e.correlation(self.e.open, self.e.volume, 10)

    def get_alpha_007(self):
        """((adv20 < volume) ? ((-1 * ts_rank(abs(delta(close, 7)), 60)) * sign(delta(close, 7))) : (-1 * 1))"""
        cond = self.e.adv20 < self.e.volume
        alpha = -1 * self.e.ts_rank(self.e.abs(self.e.delta(self.e.close, 7)), 60) * self.e.sign(self.e.delta(self.e.close, 7))
        alpha[~cond] = -1
        return alpha

    def get_alpha_008(self):
        """(-1 * rank(((sum(open, 5) * sum(returns, 5)) - delay((sum(open, 5) * sum(returns, 5)), 10))))"""
        val = self.e.ts_mean(self.e.open, 5) * self.e.ts_mean(self.e.returns, 5)
        return -1 * self.e.rank(val - self.e.delay(val, 10))

    def get_alpha_009(self):
        """((0 < ts_min(delta(close, 1), 5)) ? delta(close, 1) : ((ts_max(delta(close, 1), 5) < 0) ? delta(close, 1) : (-1 * delta(close, 1))))"""
        d = self.e.delta(self.e.close, 1)
        res = -1 * d
        res[self.e.ts_min(d, 5) > 0] = d
        res[self.e.ts_max(d, 5) < 0] = d
        return res

    def get_alpha_010(self):
        """rank(((0 < ts_min(delta(close, 1), 4)) ? delta(close, 1) : ((ts_max(delta(close, 1), 4) < 0) ? delta(close, 1) : (-1 * delta(close, 1)))))"""
        d = self.e.delta(self.e.close, 1)
        res = -1 * d
        res[self.e.ts_min(d, 4) > 0] = d
        res[self.e.ts_max(d, 4) < 0] = d
        return self.e.rank(res)

    # Simplified versions for proof-of-concept
    def get_alpha_054(self):
        """((-1 * ((low - close) * (open^5))) / ((low - high) * (close^5)))"""
        return -1 * (self.e.low - self.e.close) * (self.e.open**5) / ((self.e.low - self.e.high + 0.001) * (self.e.close**5 + 0.001))

    def get_alpha_055(self):
        """(-1 * correlation(rank(((close - ts_min(low, 12)) / (ts_max(high, 12) - ts_min(low, 12)))), rank(volume), 6))"""
        inner = (self.e.close - self.e.ts_min(self.e.low, 12)) / (self.e.ts_max(self.e.high, 12) - self.e.ts_min(self.e.low, 12) + 0.001)
        return -1 * self.e.correlation(self.e.rank(inner), self.e.rank(self.e.volume), 6)

    def get_alpha_057(self):
        """(-1 * (rank((close - vwap)) / vwap))"""
        return -1 * self.e.rank(self.e.close - self.e.vwap) / self.e.vwap

    def get_alpha_060(self):
        """(-1 * ((2 * scale(rank(((((close - low) - (high - close)) / (high - low)) * volume)))) - scale(rank(ts_argmax(close, 10)))))"""
        val1 = ((self.e.close - self.e.low) - (self.e.high - self.e.close)) / (self.e.high - self.e.low + 0.001) * self.e.volume
        return -1 * (2 * self.e.rank(val1) - self.e.rank(self.e.ts_argmax(self.e.close, 10)))

    def get_alpha_061(self):
        """(rank((vwap - ts_min(vwap, 16.1219))) < rank(correlation(vwap, adv180, 17.9282)))"""
        cond = self.e.rank(self.e.vwap - self.e.ts_min(self.e.vwap, 16)) < self.e.rank(self.e.correlation(self.e.vwap, self.e.ts_mean(self.e.volume, 180), 18))
        res = self.e.close.copy()
        res[:] = 0
        res[cond] = 1
        return res

    def get_alpha_064(self):
        """((rank(correlation(sum(((open * 0.178404) + (low * (1 - 0.178404))), 12.7498), sum(adv120, 12.7498), 16.6208)) < rank(delta(((((high + low) / 2) * 0.178404) + (vwap * (1 - 0.178404))), 3.6258))) ? -1 : 1)"""
        val1 = (self.e.open * 0.178) + (self.e.low * (1 - 0.178))
        adv120 = self.e.ts_mean(self.e.volume, 120)
        corr = self.e.correlation(self.e.ts_mean(val1, 13), self.e.ts_mean(adv120, 13), 17)
        val2 = (((self.e.high + self.e.low) / 2) * 0.178) + (self.e.vwap * (1 - 0.178))
        cond = self.e.rank(corr) < self.e.rank(self.e.delta(val2, 4))
        res = self.e.close.copy()
        res[:] = 1
        res[cond] = -1
        return res

    def get_alpha_101(self):
        """((close - open) / ((high - low) + .001))"""
        return (self.e.close - self.e.open) / ((self.e.high - self.e.low) + 0.001)

    def get_alpha_011(self):
        """((rank(ts_max((vwap - close), 3)) + rank(ts_min((vwap - close), 3))) * rank(delta(volume, 3)))"""
        return (self.e.rank(self.e.ts_max(self.e.vwap - self.e.close, 3)) + 
                self.e.rank(self.e.ts_min(self.e.vwap - self.e.close, 3))) * self.e.rank(self.e.delta(self.e.volume, 3))

    def get_alpha_012(self):
        """(sign(delta(volume, 1)) * (-1 * delta(close, 1)))"""
        return self.e.sign(self.e.delta(self.e.volume, 1)) * (-1 * self.e.delta(self.e.close, 1))

    def get_alpha_013(self):
        """(-1 * rank(covariance(rank(close), rank(volume), 5)))"""
        return -1 * self.e.rank(self.e.covariance(self.e.rank(self.e.close), self.e.rank(self.e.volume), 5))

    def get_alpha_014(self):
        """((-1 * rank(delta(returns, 3))) * correlation(open, volume, 10))"""
        return (-1 * self.e.rank(self.e.delta(self.e.returns, 3))) * self.e.correlation(self.e.open, self.e.volume, 10)

    def get_alpha_015(self):
        """(-1 * sum(rank(correlation(rank(high), rank(volume), 3)), 3))"""
        # Note: sum here usually refers to ts_sum (ts_mean * n)
        return -1 * self.e.ts_mean(self.e.rank(self.e.correlation(self.e.rank(self.e.high), self.e.rank(self.e.volume), 3)), 3) * 3

    def get_alpha_016(self):
        """(-1 * rank(covariance(rank(high), rank(volume), 5)))"""
        return -1 * self.e.rank(self.e.covariance(self.e.rank(self.e.high), self.e.rank(self.e.volume), 5))

    def get_alpha_017(self):
        """(((-1 * rank(ts_rank(close, 10))) * rank(delta(delta(close, 1), 1))) * rank(ts_rank(volume, 5)))"""
        return (-1 * self.e.rank(self.e.ts_rank(self.e.close, 10))) * \
               self.e.rank(self.e.delta(self.e.delta(self.e.close, 1), 1)) * \
               self.e.rank(self.e.ts_rank(self.e.volume, 5))

    def get_alpha_018(self):
        """(-1 * rank(((stddev(abs((close - open)), 5) + (close - open)) + correlation(close, open, 10))))"""
        return -1 * self.e.rank(self.e.ts_std(self.e.abs(self.e.close - self.e.open), 5) + \
                                (self.e.close - self.e.open) + self.e.correlation(self.e.close, self.e.open, 10))

    def get_alpha_019(self):
        """((-1 * sign(((close - delay(close, 7)) + delta(close, 7)))) * (1 + rank((1 + sum(returns, 250)))))"""
        val = (self.e.close - self.e.delay(self.e.close, 7)) + self.e.delta(self.e.close, 7)
        return (-1 * self.e.sign(val)) * (1 + self.e.rank(1 + self.e.ts_mean(self.e.returns, 250) * 250))

    def get_alpha_020(self):
        """(((-1 * rank((open - delay(high, 1)))) * rank((open - delay(close, 1)))) * rank((open - delay(low, 1))))"""
        return -1 * self.e.rank(self.e.open - self.e.delay(self.e.high, 1)) * \
               self.e.rank(self.e.open - self.e.delay(self.e.close, 1)) * \
               self.e.rank(self.e.open - self.e.delay(self.e.low, 1))

    def get_alpha_021(self):
        """((((sum(close, 8) / 8) + stddev(close, 8)) < (sum(close, 2) / 2)) ? (-1 * 1) : (((sum(close, 2) / 2) < ((sum(close, 8) / 8) - stddev(close, 8))) ? 1 : (((1 < (volume / adv20)) || ((volume / adv20) == 1)) ? 1 : (-1 * 1))))"""
        sma8 = self.e.ts_mean(self.e.close, 8)
        std8 = self.e.ts_std(self.e.close, 8)
        sma2 = self.e.ts_mean(self.e.close, 2)
        v_ratio = self.e.volume / self.e.adv20
        
        res = sma2.copy()
        res[:] = -1
        res[sma2 < (sma8 - std8)] = 1
        res[(sma2 >= (sma8 - std8)) & (v_ratio >= 1)] = 1
        res[sma2 > (sma8 + std8)] = -1
        return res

    def get_alpha_022(self):
        """(-1 * (delta(correlation(high, volume, 5), 5) * rank(stddev(close, 20))))"""
        return -1 * self.e.delta(self.e.correlation(self.e.high, self.e.volume, 5), 5) * self.e.rank(self.e.ts_std(self.e.close, 20))

    def get_alpha_023(self):
        """(((sum(high, 20) / 20) < high) ? (-1 * delta(high, 2)) : 0)"""
        cond = self.e.ts_mean(self.e.high, 20) < self.e.high
        res = self.e.high.copy()
        res[:] = 0
        res[cond] = -1 * self.e.delta(self.e.high, 2)
        return res

    def get_alpha_024(self):
        """((((delta((sum(close, 100) / 100), 100) / delay(close, 100)) < 0.05) || ((delta((sum(close, 100) / 100), 100) / delay(close, 100)) == 0.05)) ? (-1 * (close - ts_min(close, 100))) : (-1 * delta(close, 3)))"""
        sma100 = self.e.ts_mean(self.e.close, 100)
        cond = (self.e.delta(sma100, 100) / self.e.delay(self.e.close, 100)) <= 0.05
        res = -1 * self.e.delta(self.e.close, 3)
        res[cond] = -1 * (self.e.close - self.e.ts_min(self.e.close, 100))
        return res

    def get_alpha_025(self):
        """rank(((((-1 * returns) * adv20) * vwap) * (high - close)))"""
        return self.e.rank(((-1 * self.e.returns) * self.e.adv20) * self.e.vwap * (self.e.high - self.e.close))

    def get_alpha_026(self):
        """(-1 * ts_max(correlation(ts_rank(volume, 5), ts_rank(high, 5), 5), 3))"""
        return -1 * self.e.ts_max(self.e.correlation(self.e.ts_rank(self.e.volume, 5), self.e.ts_rank(self.e.high, 5), 5), 3)

    def get_alpha_027(self):
        """((0.5 < rank((sum(correlation(rank(volume), rank(vwap), 6), 2) / 2.0))) ? (-1 * 1) : 1)"""
        inner = self.e.ts_mean(self.e.correlation(self.e.rank(self.e.volume), self.e.rank(self.e.vwap), 6), 2)
        return self.e.rank(inner).applymap(lambda x: -1 if x > 0.5 else 1)

    def get_alpha_028(self):
        """scale(((correlation(adv20, low, 5) + ((high + low) / 2)) - close))"""
        # scale(x) is usually min-max scaling to 1.0 or similar. We'll use rank for simplicity in signal space
        val = self.e.correlation(self.e.adv20, self.e.low, 5) + ((self.e.high + self.e.low) / 2) - self.e.close
        return self.e.rank(val)

    def get_alpha_029(self):
        """(min(product(rank(rank(scale(log(sum(ts_min(rank(rank(-1 * rank(delta(close, 5)))), 2), 1))))), 1), 5) + ts_rank(delay((-1 * returns), 6), 5))"""
        # Note: Extremely complex nested. Simplifying to core logic: reversal signal
        return self.e.ts_rank(self.e.delay(-1 * self.e.returns, 6), 5)

    def get_alpha_030(self):
        """(((1.0 - rank(((sign((close - delay(close, 1))) + sign((delay(close, 1) - delay(close, 2)))) + sign((delay(close, 2) - delay(close, 3)))))) * sum(volume, 5)) / sum(volume, 20))"""
        combo = self.e.sign(self.e.delta(self.e.close, 1)) + self.e.sign(self.e.delta(self.e.delay(self.e.close, 1), 1)) + self.e.sign(self.e.delta(self.e.delay(self.e.close, 2), 1))
        return ((1.0 - self.e.rank(combo)) * self.e.ts_mean(self.e.volume, 5)) / self.e.ts_mean(self.e.volume, 20)

    def get_alpha_031(self):
        """((rank(rank(rank(delta(close, 10)))) * rank(correlation(adv20, low, 12))) + rank(delta(close, 3)))"""
        return (self.e.rank(self.e.delta(self.e.close, 10)) * self.e.rank(self.e.correlation(self.e.adv20, self.e.low, 12))) + self.e.rank(self.e.delta(self.e.close, 3))

    def get_alpha_032(self):
        """(scale(((sum(close, 7) / 7) - close)) + (20 * scale(correlation(vwap, delay(close, 5), 230))))"""
        val1 = self.e.ts_mean(self.e.close, 7) - self.e.close
        val2 = self.e.correlation(self.e.vwap, self.e.delay(self.e.close, 5), 230)
        return self.e.rank(val1) + (2 * self.e.rank(val2)) # Scaled weight

    def get_alpha_033(self):
        """rank(((-1 * ((rank(open) * 0.5) + (rank(close) * 0.5))) - rank(low)))"""
        return self.e.rank((-1 * ((self.e.rank(self.e.open) * 0.5) + (self.e.rank(self.e.close) * 0.5))) - self.e.rank(self.e.low))

    def get_alpha_034(self):
        """rank(((1 - rank((stddev(returns, 2) / stddev(returns, 5)))) + (1 - rank(delta(close, 1)))))"""
        val = (1 - self.e.rank(self.e.ts_std(self.e.returns, 2) / self.e.ts_std(self.e.returns, 5))) + (1 - self.e.rank(self.e.delta(self.e.close, 1)))
        return self.e.rank(val)

    def get_alpha_035(self):
        """((ts_rank(volume, 32) * (1 - ts_rank(((close + high) - low), 16))) * (1 - ts_rank(returns, 32)))"""
        return self.e.ts_rank(self.e.volume, 32) * (1 - self.e.ts_rank((self.e.close + self.e.high) - self.e.low, 16)) * (1 - self.e.ts_rank(self.e.returns, 32))

    def get_alpha_041(self):
        """(((high * low)^0.5) - vwap)"""
        return (self.e.high * self.e.low)**0.5 - self.e.vwap

    def get_alpha_043(self):
        """ts_rank((volume / adv20), 20) * ts_rank((-1 * delta(close, 7)), 8)"""
        return self.e.ts_rank(self.e.volume / self.e.adv20, 20) * self.e.ts_rank(-1 * self.e.delta(self.e.close, 7), 8)

    def get_alpha_044(self):
        """(-1 * correlation(high, rank(volume), 5))"""
        return -1 * self.e.correlation(self.e.high, self.e.rank(self.e.volume), 5)

    def get_alpha_045(self):
        """(-1 * ((rank((sum(delay(close, 5), 20) / 20)) * correlation(close, volume, 2)) * rank(correlation(sum(close, 5), sum(close, 20), 2))))"""
        term1 = self.e.rank(self.e.ts_mean(self.e.delay(self.e.close, 5), 20))
        term2 = self.e.correlation(self.e.close, self.e.volume, 2)
        term3 = self.e.rank(self.e.correlation(self.e.ts_mean(self.e.close, 5), self.e.ts_mean(self.e.close, 20), 2))
        return -1 * term1 * term2 * term3

    def get_alpha_049(self):
        """((((sum(close, 20) / 20) < (sum(close, 10) / 10)) ? (-1 * 1) : 1))"""
        cond = self.e.ts_mean(self.e.close, 20) < self.e.ts_mean(self.e.close, 10)
        res = self.e.close.copy()
        res[:] = 1
        res[cond] = -1
        return res

    def get_alpha_053(self):
        """(-1 * delta((((close - low) - (high - close)) / (high - low)), 9))"""
        num = (self.e.close - self.e.low) - (self.e.high - self.e.close)
        den = (self.e.high - self.e.low) + 0.001
        return -1 * self.e.delta(num / den, 9)

    def get_alpha_094(self):
        """((rank((vwap - ts_min(vwap, 11.5783)))^ts_rank(correlation(vwap, adv60, 4.36961), 2.38071)) * -1)"""
        corr = self.e.correlation(self.e.vwap, self.e.ts_mean(self.e.volume, 60), 4)
        return (self.e.rank(self.e.vwap - self.e.ts_min(self.e.vwap, 11)) ** self.e.ts_rank(corr, 2)) * -1

    def get_alpha_095(self):
        """(rank((open - ts_min(open, 12.4431))) < ts_rank((rank(correlation(sum(((high + low) / 2), 19.1351), sum(adv40, 19.1351), 12.8742))^5), 11.7584))"""
        val1 = (self.e.high + self.e.low) / 2
        adv40 = self.e.ts_mean(self.e.volume, 40)
        corr = self.e.correlation(self.e.ts_mean(val1, 19), self.e.ts_mean(adv40, 19), 13)
        cond = self.e.rank(self.e.open - self.e.ts_min(self.e.open, 12)) < self.e.ts_rank(self.e.rank(corr)**5, 12)
        res = self.e.close.copy()
        res[:] = 0
        res[cond] = 1
        return res

    def get_alpha_098(self):
        """(rank(correlation(vwap, sum(adv5, 26.4719), 4.58418)) - rank(correlation(rank(open), rank(adv15), 20.8272)))"""
        term1 = self.e.rank(self.e.correlation(self.e.vwap, self.e.ts_mean(self.e.volume, 5) * 26, 5))
        term2 = self.e.rank(self.e.correlation(self.e.rank(self.e.open), self.e.rank(self.e.ts_mean(self.e.volume, 15)), 21))
        return term1 - term2

    def get_alpha_099(self):
        """((rank(correlation(sum(((high + low) / 2), 19.8975), sum(adv60, 19.8975), 8.8136)) < rank(correlation(low, volume, 6.28259))) * -1)"""
        val1 = (self.e.high + self.e.low) / 2
        adv60 = self.e.ts_mean(self.e.volume, 60)
        corr1 = self.e.correlation(self.e.ts_mean(val1, 20), self.e.ts_mean(adv60, 20), 9)
        corr2 = self.e.correlation(self.e.low, self.e.volume, 6)
        cond = self.e.rank(corr1) < self.e.rank(corr2)
        res = self.e.close.copy()
        res[:] = 0
        res[cond] = -1
        return res

    def calculate_all(self):
        alphas = {}
        # Auto-run all methods starting with get_alpha
        for name in dir(self):
            if name.startswith("get_alpha_"):
                alpha_id = name.split("_")[-1]
                print(f"Calculating Alpha {alpha_id}...")
                alphas[alpha_id] = getattr(self, name)()
        return alphas
