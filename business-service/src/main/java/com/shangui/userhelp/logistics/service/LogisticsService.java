package com.shangui.userhelp.logistics.service;

import com.shangui.userhelp.logistics.domain.LogisticsInfo;

public interface LogisticsService {

    LogisticsInfo query(String trackingNo);
}
