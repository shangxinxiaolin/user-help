package com.shangui.userhelp.logistics.mapper;

import com.shangui.userhelp.logistics.domain.LogisticsInfo;

public interface LogisticsMapper {

    LogisticsInfo findByTrackingNo(String trackingNo);
}
